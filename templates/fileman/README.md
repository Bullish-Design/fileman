# Fileman — Devman component library

Minimal `lsd` wrapper that captures a repo filesystem snapshot to JSON/JSONL and prints a formatted tree in the terminal.

## Quick start

### 1. Import the devenv module

In your repo's `devenv.nix`:

```nix
{ pkgs, ... }: {
  imports = [
    ./.devman/fileman/nix/fileman.devenv.nix
  ];
}
```

### 2. Import the just recipes

In your repo's `Justfile`:

```make
import ".devman/fileman/just/fileman.just"
```

### 3. Run

```sh
just fileman:snapshot
```

This will:
- Scan the repo filesystem starting at `.`
- Write a JSONL snapshot to `.devman/out/fileman/snapshot.jsonl`
- Print a tree via `lsd --tree`
- Emit `DEV_MAN_ARTIFACT: <path>` for Devman artifact capture

## CLI usage

```
fileman snapshot [--root PATH] [--out PATH] [--jsonl|--json]
                 [--depth N] [--include-hidden] [--follow-symlinks]
                 [--exclude GLOB] [--print]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--root` | `.` | Repo root to scan |
| `--out` | `.devman/out/fileman/snapshot.jsonl` | Output file path |
| `--jsonl` | (default) | Compact single-line JSON |
| `--json` | | Pretty-printed JSON |
| `--depth` | unlimited | Max traversal depth |
| `--include-hidden` | false | Include dotfiles/dirs |
| `--follow-symlinks` | false | Follow symlinks for stat |
| `--exclude` | | Additional exclude glob (repeatable) |
| `--print` | false | Print tree via `lsd` |

## Default excludes

`.git`, `.jj`, `.hg`, `.svn`, `.devman`, `node_modules`, `__pycache__`, `.venv`, `target`, `dist`, `build`

## Snapshot schema

Output follows `fileman.snapshot.v1` — a single JSON object with `schema`, `generated_at`, `root`, `options`, and `tree` fields. See `FILEMAN_CONCEPT.md` for the full schema definition.
