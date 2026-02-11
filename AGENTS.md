# AGENTS.md

## Project Context

**Purpose:** Simple Python library that recursively scans directories, parses file metadata into Pydantic objects, and outputs structured JSON.

**MVP Target:** Use pathlib to walk directories, capture file/directory metadata (name, type, size, permissions, timestamps), structure with Pydantic, emit JSON.

**Key Insight:** No external parsers or CLI tools needed - Python's pathlib and standard library handle everything.

---

## Repository Structure

```
scripts/
  fileman                   # Main UV script

devenv.nix                  # Package management (python, uv, just)
Justfile                    # Task automation
README.md
CONCEPT_MVP_LSD.md
AGENTS.md
```

**Dead simple!** One script, standard library only.

---

## Development Workflow

### Setup

```bash
# 1. Enter devenv shell
devenv shell

# 2. Ready to use!
just scan /some/path
```

### Usage

```bash
# Scan current directory
just scan

# Scan specific path and save JSON
just scan /tmp

# Read and display saved JSON
just list

# Show files with details
just show
```

**No build steps, no external dependencies beyond Python!**

---

## Essential Skills

Detailed patterns in separate skill documents:

- **`.skills/pathlib-patterns.md`** - Recursive directory scanning, file metadata extraction
- **`.skills/pydantic-models.md`** - Data structure patterns for file entries
- **`.skills/devenv-justfile-integration.md`** - Justfile recipes, devenv configuration

---

## Common Tasks

### Run the Scanner

```bash
# Scan directory and output JSON
just scan /some/path

# Read back saved JSON
just list

# Show with pretty formatting
just show /some/path
```

### Update the Script

If you need to modify output format or add fields:

1. Edit Pydantic models in `scripts/fileman`
2. Update scanning logic
3. Test with `just scan`
4. Done!

---

## Common Pitfalls

### Path Handling Issues

**❌ Not handling permission errors:**
```python
for item in path.iterdir():  # Crashes on permission denied
    process(item)
```

**✓ Handle errors gracefully:**
```python
try:
    for item in path.iterdir():
        process(item)
except PermissionError:
    continue
```

**❌ Not resolving symlinks:**
```python
path.stat()  # Follows symlinks implicitly
```

**✓ Check if symlink first:**
```python
if path.is_symlink():
    target = path.readlink()
else:
    stat = path.stat()
```

### Pydantic Model Issues

**❌ Missing validation:**
```python
class Entry(BaseModel):
    name: str
    size: int  # Negative sizes not handled
```

**✓ Add validation:**
```python
class Entry(BaseModel):
    name: str
    size: int = Field(ge=0)
```

**❌ Circular references in recursive structures:**
```python
class Entry(BaseModel):
    children: list[Entry]  # Not defined yet
```

**✓ Use forward references:**
```python
from __future__ import annotations

class Entry(BaseModel):
    children: list[Entry] = []
```

---

## Justfile Quick Reference

```make
# Usage commands
just scan PATH              # Scan directory and save JSON
just list                   # Display saved JSON entries
just show PATH              # Pretty print with details

# Development
just test                   # Run validation tests
```

---

## MVP Acceptance Criteria

### Setup

- [ ] devenv shell loads without errors
- [ ] `fileman` script is executable
- [ ] UV dependencies load correctly

### Functionality

- [ ] Script recursively scans directories
- [ ] Captures file metadata (name, type, size, permissions, timestamps)
- [ ] Produces valid Pydantic models
- [ ] Outputs valid JSON
- [ ] Handles files, directories, and symlinks
- [ ] Handles permission errors gracefully

### Usage

- [ ] `just scan /path` works on real directories
- [ ] JSON output is valid and well-formed
- [ ] Can read back and display JSON data
- [ ] Output includes all required fields

---

## Testing

Manual testing for MVP:

```bash
# Test on various directories
just scan /tmp
just scan /home/user
just scan .

# Verify JSON structure
just scan . && cat filetree.json | jq .

# Test reading back
just list
```

**Use real directories to verify:**
- Proper recursive scanning
- Symlink handling
- Permission error handling
- Large directory performance

---

## Key Questions Before Starting

### Setup Questions

1. Does `devenv shell` load successfully?
2. Is Python 3.12+ available?
3. Is UV configured correctly?

### Implementation Questions

1. Does pathlib recursively scan directories?
2. Are file stats captured correctly?
3. Do Pydantic models validate properly?
4. Is JSON output well-formed?

### Before Declaring Complete

1. Does `just scan /path` work on real directories?
2. Is the JSON output valid (test with `jq`)?
3. Can you read back and display the data?
4. Are acceptance criteria met?

---

## Success Criteria

**You're done when:**
- `devenv shell` loads successfully
- `just scan /path` produces valid JSON
- Output contains all file metadata
- Can read back and display entries
- Handles edge cases (symlinks, permissions)

**You're NOT done when:**
- Script crashes on permission errors
- JSON is malformed
- Missing required metadata fields
- Can't handle symlinks correctly

---

## Environment Setup

**devenv.nix provides:**
- python312 + uv (for script execution)
- just (task runner)
- jq (for JSON validation)

**No external tools or parsers needed!** Pure Python stdlib + Pydantic.

---

## Data Structure

### Target Output Format

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
    },
    {
      "path": "/path/to/directory",
      "name": "directory",
      "type": "directory",
      "size": 4096,
      "permissions": "rwxr-xr-x",
      "modified": "2025-02-10T09:10:00"
    },
    {
      "path": "/path/to/link",
      "name": "link",
      "type": "symlink",
      "target": "/target/path",
      "permissions": "rwxrwxrwx",
      "modified": "2025-02-10T09:20:15"
    }
  ]
}
```

### Pydantic Model Pattern

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime

class FileEntry(BaseModel):
    path: str
    name: str
    type: str = Field(pattern="^(file|directory|symlink)$")
    size: int = Field(ge=0)
    permissions: str
    modified: datetime
    extension: str | None = None
    target: str | None = None  # For symlinks

class FileTree(BaseModel):
    root: str
    scanned_at: datetime
    entries: list[FileEntry]
```

---

## References

### Documentation

- Python pathlib: https://docs.python.org/3/library/pathlib.html
- Pydantic: https://docs.pydantic.dev/
- UV scripts: https://docs.astral.sh/uv/guides/scripts/
- Justfile: https://just.systems/man/en/

### Project Files

- `CONCEPT_MVP_LSD.md` - MVP specification
- `Justfile` - Task automation
- `devenv.nix` - Package management
- `scripts/fileman` - Main script
