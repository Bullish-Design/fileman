# AGENTS.md — Build Fileman from scratch (Devman component library)

This doc is written for an automation/agent that needs to create **Fileman** end-to-end as a **Devman template component library**.

**Read first (required):**
1) `DEVMAN_CORE_CONCEPTS.md` (Devman first principles, store/instance/symlink/run model)
2) `FILEMAN_CONCEPT.md` (Fileman’s goals, layout, CLI shape, devenv/just patterns)

---

## 0) Success criteria (Definition of Done)

You are done when all of these are true:

- `fileman snapshot`:
  - scans a repo root
  - writes **one JSON snapshot object** to a file (JSON or JSONL)
  - prints a clean terminal tree (via `lsd --tree`) when `--print` is set
- The **default output path** is under `.devman/out/fileman/…`
- The `just` recipe:
  - is **idempotent**
  - prints an artifact marker line `DEV_MAN_ARTIFACT: <path>`
  - supports Devman’s “run model” expectations (writes outputs to `.devman/out/…`)
- `nix/fileman.devenv.nix` is **importable** by other Devman libraries/repos (`imports = [ ./.devman/fileman/nix/fileman.devenv.nix ];`)
- The template payload follows Devman’s **store + instance + symlink semantics** (no repo-local state outside `.devman/out/…`)

---

## 1) Create the Devman template skeleton

Devman’s canonical store layout is:

```
<DEV_MAN_STORE>/
  templates/
    fileman/
      .devman/
        templates/
          fileman/
            ...payload...
      manifest.toml
```

Create this folder structure:

```
templates/fileman/
  .devman/templates/fileman/
    nix/
    just/
    bin/
    src/
  manifest.toml
  .gitignore
  README.md
  FILEMAN_CONCEPT.md
  AGENTS.md
```

### 1.1 manifest.toml (minimal)
You don’t have the full manifest schema here. Keep it minimal and consistent with other templates in the same store.

Suggested minimal shape (adjust keys to match your Devman implementation):

```toml
name = "fileman"
version = "0.1.0"
type = "component-library"
description = "Minimal lsd wrapper to snapshot repo filesystem -> JSON/JSONL and print tree"
```

If your store requires additional fields (entry points, hooks, links), copy the pattern from an existing template in the store.

### 1.2 .gitignore (template repo only)
If Fileman itself lives in git (not required), ignore outputs:

```
.devman/out/
```

---

## 2) Implement the Fileman payload

All runtime bits belong inside:

```
templates/fileman/.devman/templates/fileman/
```

### 2.1 Importable devenv module: `nix/fileman.devenv.nix`

Create:

`templates/fileman/.devman/templates/fileman/nix/fileman.devenv.nix`

Use `lsd`, and a Python env with `pydantic` (and nothing else).

```nix
{ pkgs, ... }:
let
  py = pkgs.python3.withPackages (ps: [ ps.pydantic ]);

  fileman = pkgs.writeShellApplication {
    name = "fileman";
    runtimeInputs = [ py pkgs.lsd ];
    text = ''
      # Expect to run inside a repo that has .devman -> instance symlink.
      exec python3 ./.devman/fileman/src/fileman_snapshot.py "$@"
    '';
  };
in
{
  packages = [
    pkgs.lsd
    py
    fileman
  ];
}
```

Notes:
- Keep this module **import-only**: it should not assume anything besides `.devman/fileman/...` being present.
- `fileman_snapshot.py` lives in the instance, so the relative path is stable.

---

### 2.2 Just recipes: `just/fileman.just`

Create:

`templates/fileman/.devman/templates/fileman/just/fileman.just`

Goals:
- single primary recipe: `fileman:snapshot`
- write artifacts to `.devman/out/fileman`
- print `DEV_MAN_ARTIFACT: <path>` so Devman can capture it

```make
# fileman.just — import from a repo's Justfile
# Usage:
#   import ".devman/fileman/just/fileman.just"
#
# Then run:
#   just fileman:snapshot

fileman:snapshot root="." out=".devman/out/fileman/snapshot.jsonl" depth="" include_hidden="false":
  mkdir -p .devman/out/fileman

  if [ "${DEV_MAN_SIMULATE:-0}" = "1" ]; then     echo "[simulate] would run fileman snapshot --root {{root}} --out {{out}} --jsonl";     echo "DEV_MAN_ARTIFACT: {{out}}";     exit 0;   fi

  EXTRA=""
  if [ -n "{{depth}}" ]; then EXTRA="$EXTRA --depth {{depth}}"; fi
  if [ "{{include_hidden}}" = "true" ]; then EXTRA="$EXTRA --include-hidden"; fi

  fileman snapshot --root "{{root}}" --out "{{out}}" --jsonl --print $EXTRA

  echo "DEV_MAN_ARTIFACT: {{out}}"
```

---

### 2.3 CLI entrypoint script: `src/fileman_snapshot.py`

Create:

`templates/fileman/.devman/templates/fileman/src/fileman_snapshot.py`

Requirements:
- fast scan via `os.scandir()`
- default excludes include **`.devman`** and `.git`
- write a **single JSON object** (JSONL: one line)
- print tree using `lsd` (not your own tree renderer)

**Minimal implementation (copy/paste):**

```python
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
```

Make sure it is executable in the store template (optional):

```
chmod +x templates/fileman/.devman/templates/fileman/src/fileman_snapshot.py
```

---

## 3) Add the optional `bin/` shim (only if your store wants it)

If you prefer a repo-local shim outside Nix:

`templates/fileman/.devman/templates/fileman/bin/fileman`

```sh
#!/usr/bin/env sh
exec python3 "$(dirname "$0")/../src/fileman_snapshot.py" "$@"
```

(But the **preferred** entrypoint for Devman usage is the one provided by `devenv.nix`.)

---

## 4) Create template-level docs

Ensure these exist (they guide consumers):

- `FILEMAN_CONCEPT.md` (already written)
- `README.md` (short “how to attach/import/run”)
- `AGENTS.md` (this file)

**README.md minimal content** should include:
- how to import:
  - `imports = [ ./.devman/fileman/nix/fileman.devenv.nix ];`
- how to run:
  - `import ".devman/fileman/just/fileman.just"`
  - `just fileman:snapshot`

---

## 5) Validation steps (must run)

### 5.1 Validate in a repo with `.devman` link present
From the repo root:

1) Ensure devenv includes Fileman:

```nix
# devenv.nix (consumer repo)
{ pkgs, ... }: {
  imports = [
    ./.devman/fileman/nix/fileman.devenv.nix
  ];
}
```

2) Ensure Justfile imports recipes:

```make
import ".devman/fileman/just/fileman.just"
```

3) Run:

```sh
just fileman:snapshot
```

Expected:
- terminal prints `lsd --tree` output
- snapshot written to `.devman/out/fileman/snapshot.jsonl`
- last line includes `DEV_MAN_ARTIFACT: .devman/out/fileman/snapshot.jsonl`

### 5.2 Quick sanity checks on output
- JSONL file contains exactly **one line**
- The JSON includes:
  - `schema: fileman.snapshot.v1`
  - `generated_at`
  - `tree.type == "dir"`
  - `options.exclude` includes `.devman`

---

## 6) Quality & Devman constraints checklist

- ✅ **Just-first**: primary interface is `just fileman:snapshot`
- ✅ **Store-owned artifacts**: writes only under `.devman/out/fileman/…`
- ✅ **Symlink-friendly**: never traverses `.devman/` by default
- ✅ **Safe-by-default**: no destructive operations; simulate mode supported
- ✅ **Idempotent**: re-running overwrites snapshot file
- ✅ **Composable**: imported `devenv.nix` module + just fragment

---

## 7) Optional enhancements (only after minimal passes)

Keep these behind flags to preserve speed:

- `--sort name` for deterministic tree ordering (slower)
- `--hash` to add file hashes (expensive; off by default)
- `--stream` JSONL mode to emit one record per node (no full tree in memory)
- include `git` context: current commit, dirty flag (cheap)

