#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, Field


# -----------------
# Models
# -----------------

class Node(BaseModel):
    type: str
    name: str
    relpath: str
    mode: int
    uid: int
    gid: int
    mtime_ns: int
    inode: int
    dev: int


class FileNode(Node):
    type: str = Field(default="file")
    size: int


class SymlinkNode(Node):
    type: str = Field(default="symlink")
    target: str


class DirNode(Node):
    type: str = Field(default="dir")
    children: List[Node] = Field(default_factory=list)


AnyNode = Union[FileNode, SymlinkNode, DirNode]


# -----------------
# Scan options
# -----------------

DEFAULT_EXCLUDES: Tuple[str, ...] = (
    ".git",
    ".jj",
    ".hg",
    ".svn",
    ".devman",
    "node_modules",
    "__pycache__",
    ".venv",
    "target",
    "dist",
    "build",
)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def is_hidden(name: str) -> bool:
    return name.startswith(".")

def excluded(name: str, relpath: str, patterns: Sequence[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(relpath, pat):
            return True
    return False

def relpath(root: Path, p: Path) -> str:
    # Portable snapshot paths
    return str(p.relative_to(root)).replace(os.sep, "/")

def scan_tree(
    root: Path,
    *,
    max_depth: Optional[int],
    include_hidden: bool,
    follow_symlinks: bool,
    exclude_globs: Sequence[str],
) -> DirNode:
    root = root.resolve()
    st = root.stat()

    root_node = DirNode(
        name=".",
        relpath=".",
        mode=st.st_mode,
        uid=getattr(st, "st_uid", 0),
        gid=getattr(st, "st_gid", 0),
        mtime_ns=st.st_mtime_ns,
        inode=getattr(st, "st_ino", 0),
        dev=getattr(st, "st_dev", 0),
        children=[],
    )

    stack: List[Tuple[Path, DirNode, int]] = [(root, root_node, 0)]

    while stack:
        dpath, dnode, depth = stack.pop()
        if max_depth is not None and depth >= max_depth:
            continue

        try:
            with os.scandir(dpath) as it:
                for e in it:
                    name = e.name
                    if not include_hidden and is_hidden(name):
                        continue

                    p = Path(e.path)
                    rp = relpath(root, p)

                    if excluded(name, rp, exclude_globs):
                        continue

                    try:
                        st = e.stat(follow_symlinks=follow_symlinks)
                    except OSError:
                        continue

                    base = dict(
                        name=name,
                        relpath=rp,
                        mode=st.st_mode,
                        uid=getattr(st, "st_uid", 0),
                        gid=getattr(st, "st_gid", 0),
                        mtime_ns=st.st_mtime_ns,
                        inode=getattr(st, "st_ino", 0),
                        dev=getattr(st, "st_dev", 0),
                    )

                    if e.is_symlink():
                        try:
                            target = os.readlink(e.path)
                        except OSError:
                            target = ""
                        dnode.children.append(SymlinkNode(**base, target=target))
                        continue

                    if e.is_dir(follow_symlinks=follow_symlinks):
                        child = DirNode(**base, children=[])
                        dnode.children.append(child)
                        stack.append((p, child, depth + 1))
                    else:
                        dnode.children.append(FileNode(**base, size=st.st_size))
        except OSError:
            continue

    return root_node

def write_snapshot(tree: DirNode, out: Path, *, jsonl: bool, meta: dict) -> None:
    payload = {
        "schema": "fileman.snapshot.v1",
        "generated_at": now_iso(),
        **meta,
        "tree": tree.model_dump(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        if jsonl:
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
        else:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")

def print_tree_with_lsd(root: Path, *, depth: Optional[int], include_hidden: bool) -> None:
    cmd = ["lsd", "--tree", "--icon", "never", "--ignore-config"]
    # Prefer no-color when possible; `lsd` flag support can vary by build.
    # NO_COLOR is widely recognized; `lsd` also respects config when not ignored.
    env = dict(os.environ)
    env["NO_COLOR"] = "1"

    if include_hidden:
        cmd.append("-a")
    if depth is not None:
        cmd += ["--depth", str(depth)]

    cmd.append(str(root))

    subprocess.run(cmd, env=env, check=False)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fileman")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("snapshot", help="snapshot repo filesystem -> JSON/JSONL; optionally print tree")
    s.add_argument("--root", default=".", help="repo root (default: .)")
    s.add_argument("--out", default=".devman/out/fileman/snapshot.jsonl", help="output file path")
    fmt = s.add_mutually_exclusive_group()
    fmt.add_argument("--jsonl", action="store_true", help="write compact JSONL (one JSON object per line)")
    fmt.add_argument("--json", action="store_true", help="write pretty JSON")
    s.add_argument("--depth", type=int, default=None, help="max depth (default: unlimited)")
    s.add_argument("--include-hidden", action="store_true", help="include dotfiles/dirs")
    s.add_argument("--follow-symlinks", action="store_true", help="follow symlinks for stat/is_dir")
    s.add_argument("--exclude", action="append", default=[], help="exclude glob (repeatable)")
    s.add_argument("--print", dest="do_print", action="store_true", help="print tree via lsd")
    return p

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "snapshot":
        root = Path(args.root)
        out = Path(args.out)

        exclude = list(DEFAULT_EXCLUDES) + list(args.exclude or [])
        tree = scan_tree(
            root,
            max_depth=args.depth,
            include_hidden=args.include_hidden,
            follow_symlinks=args.follow_symlinks,
            exclude_globs=exclude,
        )

        jsonl = True
        if args.json:
            jsonl = False
        elif args.jsonl:
            jsonl = True

        meta = {
            "root": str(root),
            "options": {
                "depth": args.depth,
                "include_hidden": args.include_hidden,
                "follow_symlinks": args.follow_symlinks,
                "exclude": exclude,
            },
        }

        write_snapshot(tree, out, jsonl=jsonl, meta=meta)

        if args.do_print:
            print_tree_with_lsd(root, depth=args.depth, include_hidden=args.include_hidden)

        return 0

    return 2

if __name__ == "__main__":
    raise SystemExit(main())
