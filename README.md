# fileman

A minimal Python MVP for recursively scanning directories and producing structured JSON metadata.

## Features

- Recursive filesystem scanning via `pathlib`
- Metadata captured for files, directories, and symlinks
- Structured models with Pydantic validation
- JSON output plus read-back display commands

## Commands

From a `devenv shell`, use:

```bash
just scan /some/path
just list
just show
```

Direct script usage:

```bash
uv run scripts/fileman scan /some/path
uv run scripts/fileman list filetree.json
uv run scripts/fileman show filetree.json
```

## Output format

`scan` writes `filetree.json` with this shape:

```json
{
  "root": "/path/to/scan",
  "scanned_at": "2025-02-10T10:30:45",
  "entries": [
    {
      "path": "/path/to/file.txt",
      "name": "file.txt",
      "type": "file",
      "size": 1234,
      "permissions": "rw-r--r--",
      "modified": "2025-02-10T09:15:30",
      "extension": ".txt"
    }
  ]
}
```

## Notes

- Permission errors are skipped during scans.
- Symlinks are captured as type `symlink` and include a `target` field.
