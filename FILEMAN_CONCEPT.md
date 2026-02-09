# Fileman — Devman component concept
*A minimal `lsd` wrapper that captures a repo filesystem snapshot to JSON/JSONL and prints a formatted tree in the terminal.*

## Goals
- **Fast, low-overhead repo scan** that captures **file + directory metadata** into a **single JSON snapshot object**.
- Optionally write as **JSONL** (one snapshot per line; default is one line).
- Print a **human-readable tree** to the terminal using **`lsd`** for formatting.
- Ship as a **Devman template component library** that can be:
  - attached to many repos via Devman instance symlinks
  - reused by other Devman libraries via **importable `devenv.nix` modules**
  - executed via **`just` recipes** (Devman’s “just-first” execution model).

## Non-goals
- Persistent, stable IDs that survive renames/copies across time (that’s a different tool class).
- Git-history tracking (can be layered later as an optional “git context” extension).

---

## How Fileman fits the Devman mental model
Fileman is designed to obey Devman’s core constraints:

- **Just-first**: users run `just fileman:snapshot …`, not ad-hoc scripts.
- **Store-owned artifacts**: snapshots are written to `.devman/out/fileman/…` so Devman can capture them as run artifacts.
- **Symlink consumption**: Fileman’s scripts/config live under the instance `.devman/…` and appear in the repo via the `.devman -> store` symlink.
- **devenv-first**: Fileman exposes a `devenv.nix` module so any repo (or other Devman library) can import it.

---

## Template/component layout (in the Devman Store)
This is a minimal, composable “component library” template named `fileman`.

```
<DEV_MAN_STORE>/
  templates/
    fileman/
      .devman/
        templates/
          fileman/
            README.md
            nix/
              fileman.devenv.nix
            just/
              fileman.just
            bin/
              fileman   # small wrapper, calls python module
            src/
              fileman_snapshot.py
            FILEMAN_CONCEPT.md
        manifest.toml
```

### How it appears inside a repo
Because the repo’s `.devman/` is a symlink into the instance, Fileman material becomes available at predictable paths like:

```
<REPO>/.devman/fileman/
  nix/fileman.devenv.nix
  just/fileman.just
  bin/fileman
  src/fileman_snapshot.py
```

Other Devman libraries and the repo’s own `devenv.nix` can import from `./.devman/fileman/nix/fileman.devenv.nix`.

---

## CLI design: minimal `lsd` wrapper
Fileman provides a single CLI entrypoint, `fileman`, with one primary command.

### Command
`fileman snapshot`

### Responsibilities
1. **Scan filesystem** starting at repo root:
   - Use a fast traversal (`os.scandir` in Python).
   - Default excludes: `.git`, `.devman`, `node_modules`, `target`, etc.
2. **Build JSON snapshot**:
   - Single JSON object with schema version + metadata + tree.
3. **Write JSON**:
   - `--json` pretty JSON (default)
   - `--jsonl` compact one-line JSON (recommended for artifacts/logging)
4. **Print tree**:
   - Delegate formatting to `lsd --tree` for a clean terminal view.
   - Disable icons/colors for stable text output (works well in logs).

### Suggested flags
- `--root PATH` (default `.`)
- `--out PATH` (default `.devman/out/fileman/snapshot.jsonl`)
- `--jsonl` (default true for Devman runs; optionally allow `--json`)
- `--depth N` (optional)
- `--include-hidden`
- `--follow-symlinks` (default false)
- `--exclude GLOB` (repeatable)

---

## Snapshot JSON schema (v1)
A single JSON object:

```json
{
  "schema": "fileman.snapshot.v1",
  "generated_at": "2026-02-09T15:04:05Z",
  "root": ".",
  "options": {
    "depth": null,
    "include_hidden": false,
    "follow_symlinks": false,
    "exclude": [".git", ".devman", "node_modules"]
  },
  "tree": {
    "type": "dir",
    "name": ".",
    "relpath": ".",
    "mode": 16877,
    "uid": 501,
    "gid": 20,
    "mtime_ns": 1700000000000000000,
    "inode": 123456,
    "dev": 16777231,
    "children": [
      { "type": "file", "name": "README.md", "relpath": "README.md", "size": 1024, "...": "..." },
      { "type": "dir", "name": "src", "relpath": "src", "children": [ ... ] }
    ]
  }
}
```

Notes:
- Keep paths **relative** to root for portability.
- Store timestamps as `mtime_ns` (int) for lossless sorting/diffing.
- `mode/uid/gid/inode/dev` are optional on platforms where they’re unavailable.

---

## `lsd` printing strategy
Fileman uses `lsd` **only** for terminal display.

Recommended invocation (stable, log-friendly):

- Tree view: `--tree`
- Disable icons: `--icon never`
- Ignore user configs for reproducibility: `--ignore-config`
- Disable colors: use `--color never` if available in your `lsd` build, or rely on `classic`/config; otherwise set `NO_COLOR=1`.

Example:

```sh
lsd --tree --icon never --ignore-config --color never .
```

If your `lsd` doesn’t support a `--color` flag, rely on `--ignore-config` and `NO_COLOR=1` (and/or a project-local `lsd` config set to never colorize).

---

## `devenv.nix` module (importable)
Fileman ships a `devenv` module that:
- installs `lsd` and Python
- exposes `fileman` on `$PATH` as a script

`nix/fileman.devenv.nix`:

```nix
{ pkgs, ... }:
let
  fileman = pkgs.writeShellApplication {
    name = "fileman";
    runtimeInputs = [ pkgs.python3 pkgs.lsd ];
    text = ''
      exec python3 ./.devman/fileman/src/fileman_snapshot.py "$@"
    '';
  };
in
{
  packages = [
    pkgs.lsd
    pkgs.python3
    fileman
  ];
}
```

### How another Devman library (or the repo) imports it
In the consuming repo’s `devenv.nix` (or a higher-level library’s module):

```nix
{ pkgs, ... }: {
  imports = [
    ./.devman/fileman/nix/fileman.devenv.nix
  ];
}
```

This works because `.devman/` exists in the repo as a symlink into the instance.

---

## Minimal Python implementation outline
Place the scanner at `.devman/fileman/src/fileman_snapshot.py`.

Key points:
- Use `os.scandir()` recursion for speed.
- Do **not** sort by default (fastest); optionally provide `--sort name` if you need deterministic diffs.
- Always exclude `.devman` by default to avoid snapshotting the store symlink contents.

Pseudo-structure:

- `scan(root, options) -> tree`
- `write_snapshot(tree, out_path, jsonl=True)`
- `print_tree_via_lsd(root, depth=None, include_hidden=False)`

---

## `just` integration (Devman-first execution)
Ship a `just` fragment at `.devman/fileman/just/fileman.just`:

```make
# fileman.just

fileman:snapshot root="." out=".devman/out/fileman/snapshot.jsonl" depth="":
  mkdir -p .devman/out/fileman
  if [ -n "{{depth}}" ]; then     fileman snapshot --root "{{root}}" --out "{{out}}" --jsonl --depth "{{depth}}" --print;   else     fileman snapshot --root "{{root}}" --out "{{out}}" --jsonl --print;   fi
  echo "DEV_MAN_ARTIFACT: {{out}}"
```

Then, in the repo’s main `Justfile`, import the fragment (or copy recipes into the repo Justfile if you prefer):

```make
import ".devman/fileman/just/fileman.just"
```

---

## Operational notes
- **Artifact location**: `.devman/out/fileman/…` is the default to align with Devman artifact capture.
- **Safe by default**: Fileman should only read the filesystem and write outputs under `.devman/out/`.
- **Idempotent**: Running snapshot repeatedly should overwrite the target output path (or write timestamped outputs if you prefer).

---

## Future extensions (optional)
- Add `--git-context` (capture current VCS state into snapshot metadata).
- Add `--hash` to include content hashes for selected file types (expensive; off by default).
- Add `--stream` mode to emit one JSONL record per node for huge repos (no full tree in memory).

