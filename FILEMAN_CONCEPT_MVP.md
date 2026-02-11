# CONCEPT — `fileman` MVP (Pure Python Pathlib)

## Goal
Create a simple Python library that recursively scans directories, captures file metadata, structures it with Pydantic, and outputs JSON. Can also read back and display the data in a formatted view.

**MVP focus:** Use pathlib for directory walking, Pydantic for data validation, standard library only.

---

## Architecture

### Components
1. **UV script:** Main scanning and display logic
2. **Pydantic models:** Data structure definitions
3. **devenv.nix:** Package management (python, uv, just)
4. **Justfile:** Basic commands for usage

### Data flow
```
pathlib.Path.rglob() → stat() metadata → Pydantic models → JSON file
JSON file → Pydantic.model_validate_json() → display formatted
```

### Simplification
This is a **minimal MVP** using:
- Python standard library (pathlib, stat, json)
- Pydantic for validation
- UV for script execution
- No external CLI tools or parsers

---

## Target Data Structure

### File Metadata to Capture

```python
# For each file/directory entry:
- path: absolute path
- name: filename/dirname
- type: "file" | "directory" | "symlink"
- size: bytes (from stat.st_size)
- permissions: string format (e.g., "rwxr-xr-x")
- modified: datetime (from stat.st_mtime)
- extension: file extension (for files only)
- target: symlink target path (for symlinks only)
```

### JSON Output Format
```json
{
  "root": "/path/to/scan",
  "scanned_at": "2025-02-10T10:30:45.123456",
  "entries": [
    {
      "path": "/path/to/scan/file.txt",
      "name": "file.txt",
      "type": "file",
      "size": 1234,
      "permissions": "rw-r--r--",
      "modified": "2025-02-10T09:15:30.000000",
      "extension": ".txt"
    },
    {
      "path": "/path/to/scan/subdir",
      "name": "subdir",
      "type": "directory",
      "size": 4096,
      "permissions": "rwxr-xr-x",
      "modified": "2025-02-10T09:10:00.000000"
    },
    {
      "path": "/path/to/scan/link",
      "name": "link",
      "type": "symlink",
      "target": "/target/path",
      "permissions": "rwxrwxrwx",
      "modified": "2025-02-10T09:20:15.000000"
    }
  ]
}
```

**MVP scope:** Recursive scan, full metadata capture, clean JSON output

---

## Pydantic Models

### Data Structure
```python
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class FileEntry(BaseModel):
    """Single file/directory/symlink entry."""
    path: str
    name: str
    type: Literal["file", "directory", "symlink"]
    size: int = Field(ge=0, description="Size in bytes")
    permissions: str = Field(pattern=r"^[rwx-]{9}$")
    modified: datetime
    extension: str | None = Field(default=None, description="File extension")
    target: str | None = Field(default=None, description="Symlink target")

class FileTree(BaseModel):
    """Complete scan result."""
    root: str
    scanned_at: datetime
    entries: list[FileEntry]
```

**Key features:**
- Type validation with Literal
- Size validation (non-negative)
- Permission format validation
- Optional fields for extension/target
- Timestamp capture

---

## Core Logic

### Directory Scanning
```python
from pathlib import Path
from datetime import datetime
import stat

def scan_directory(root: Path) -> FileTree:
    """Recursively scan directory and build FileTree."""
    entries = []
    
    try:
        for item in root.rglob("*"):
            try:
                entry = process_path(item)
                entries.append(entry)
            except (PermissionError, OSError):
                # Skip inaccessible items
                continue
    except (PermissionError, OSError):
        # Root directory inaccessible
        pass
    
    return FileTree(
        root=str(root.absolute()),
        scanned_at=datetime.now(),
        entries=entries
    )
```

### Path Processing
```python
def process_path(path: Path) -> FileEntry:
    """Extract metadata from a single path."""
    
    # Determine type
    if path.is_symlink():
        entry_type = "symlink"
        target = str(path.readlink())
        # Use lstat for symlink info
        st = path.lstat()
    elif path.is_dir():
        entry_type = "directory"
        target = None
        st = path.stat()
    else:
        entry_type = "file"
        target = None
        st = path.stat()
    
    # Convert permissions to string format
    permissions = stat.filemode(st.st_mode)[1:]  # Skip first char
    
    # Get extension for files
    extension = path.suffix if entry_type == "file" else None
    
    return FileEntry(
        path=str(path.absolute()),
        name=path.name,
        type=entry_type,
        size=st.st_size,
        permissions=permissions,
        modified=datetime.fromtimestamp(st.st_mtime),
        extension=extension,
        target=target
    )
```

**Key considerations:**
- Use `rglob("*")` for recursive scanning
- Handle permission errors gracefully
- Use `lstat()` for symlinks (don't follow)
- Use `stat()` for regular files/dirs
- Convert mode to string format

---

## Script Structure

### Main UV Script (scripts/fileman)
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic>=2.0",
# ]
# ///

from __future__ import annotations
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal
import json
import sys
import stat

# [Pydantic models here]

# [Core logic functions here]

def cmd_scan(path: str, output: str = "filetree.json"):
    """Scan directory and save to JSON."""
    root = Path(path).resolve()
    tree = scan_directory(root)
    
    with open(output, "w") as f:
        f.write(tree.model_dump_json(indent=2))
    
    print(f"Scanned {len(tree.entries)} entries to {output}")

def cmd_list(input_file: str = "filetree.json"):
    """Read JSON and list entries."""
    with open(input_file) as f:
        tree = FileTree.model_validate_json(f.read())
    
    for entry in tree.entries:
        print(f"{entry.type:9} {entry.path}")

def cmd_show(input_file: str = "filetree.json"):
    """Read JSON and show detailed view."""
    with open(input_file) as f:
        tree = FileTree.model_validate_json(f.read())
    
    print(f"Root: {tree.root}")
    print(f"Scanned: {tree.scanned_at}")
    print(f"Entries: {len(tree.entries)}\n")
    
    for entry in tree.entries:
        target = f" -> {entry.target}" if entry.target else ""
        ext = entry.extension or ""
        size = format_size(entry.size)
        print(f"{entry.permissions} {size:>8} {entry.modified:%Y-%m-%d %H:%M} "
              f"{entry.name}{ext}{target}")

def format_size(size: int) -> str:
    """Format size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fileman {scan|list|show} [path]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else "."
    
    if cmd == "scan":
        cmd_scan(path)
    elif cmd == "list":
        cmd_list(path if path != "." else "filetree.json")
    elif cmd == "show":
        cmd_show(path if path != "." else "filetree.json")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
```

**Script features:**
- Three commands: scan, list, show
- UV inline dependencies
- All logic in single file
- Clean command interface

---

## Testing Strategy

### Manual Validation
```bash
# Test scanning
just scan /tmp
cat filetree.json | jq .

# Test listing
just list

# Test display
just show

# Verify data structure
cat filetree.json | jq '.entries[0]'
```

### Edge Case Testing
```bash
# Test permission errors
just scan /root  # Should handle gracefully

# Test symlinks
mkdir test_dir
ln -s /tmp test_dir/link
just scan test_dir

# Test large directory
just scan /usr/lib  # Performance test
```

**Manual testing covers:**
- Basic functionality
- Edge cases (permissions, symlinks)
- Performance on real directories
- JSON validity

---

## devenv Configuration

### devenv.nix - Package Management
```nix
{ pkgs, ... }:
{
  packages = with pkgs; [
    just          # Task runner
    uv            # Python management 
    jq            # JSON validation
  ];

  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv.enable = true;
  };

  scripts = {
    fileman.exec = "uv run scripts/fileman \"$@\"";
  };
}
```

**No complex setup** - just basic packages!

---

## Justfile Commands

### Task Automation
```make
# Default - show help
default:
    @just --list

# Scan directory and save JSON
scan PATH=".":
    fileman scan {{PATH}}

# List entries from saved JSON
list INPUT="filetree.json":
    fileman list {{INPUT}}

# Show detailed view
show INPUT="filetree.json":
    fileman show {{INPUT}}

# Validate JSON structure
validate INPUT="filetree.json":
    jq empty {{INPUT}}

# Count entries
count INPUT="filetree.json":
    jq '.entries | length' {{INPUT}}

# Show only files
files INPUT="filetree.json":
    jq '.entries[] | select(.type=="file") | .path' {{INPUT}}
```

**Simple recipes** for common operations!

---

## Repository Structure

```
fileman/
  scripts/
    fileman                   # Main UV script
  Justfile                    # Task automation
  devenv.nix                  # Package management
  README.md
  CONCEPT_MVP_LSD.md
  AGENTS.md
  filetree.json               # Output file (generated)
```

**Minimal structure** - one script, supporting files!

---

## Usage Workflow

### Setup
```bash
# Enter devenv shell
devenv shell

# Ready to use immediately!
```

### Typical Usage
```bash
# Scan a directory
just scan /path/to/dir

# View results
just list           # Simple list
just show           # Detailed view

# Process JSON
jq '.entries[] | select(.type=="file")' filetree.json
```

### Integration Example
```bash
# Scan and extract specific info
just scan /project
jq '.entries[] | select(.extension==".py") | .path' filetree.json

# Count file types
jq '.entries | group_by(.type) | map({type: .[0].type, count: length})' \
   filetree.json
```

---

## MVP Acceptance Criteria

### Setup
- [ ] devenv shell loads without errors
- [ ] `fileman` command is available
- [ ] UV dependencies load correctly

### Functionality
- [ ] Recursively scans directories
- [ ] Captures all metadata fields
- [ ] Produces valid Pydantic models
- [ ] Outputs well-formed JSON
- [ ] Handles files, directories, symlinks
- [ ] Gracefully handles permission errors
- [ ] Can read back and display data

### Usage
- [ ] `just scan /path` works on real directories
- [ ] JSON output validates with jq
- [ ] `just list` displays entries
- [ ] `just show` formats output nicely
- [ ] No manual configuration needed

---

## Future Enhancements

Potential additions (post-MVP):
- Filtering options (by type, size, date)
- Include/exclude patterns
- Parallel scanning for performance
- Different output formats (CSV, YAML)
- Comparison between scans
- Hash calculation for files

**MVP keeps it simple:**
- Single scan mode
- JSON output only
- Basic display modes

---

## Success Metrics

MVP is complete when:
1. `devenv shell` loads successfully
2. `just scan /path` produces valid JSON
3. JSON contains all required metadata
4. Can read back and display data
5. Handles edge cases gracefully
6. Works on real directories

---

## Key Advantages

**This pure Python approach:**
- ✅ No external CLI tools needed
- ✅ No parser development
- ✅ Standard library only (+ Pydantic)
- ✅ Type-safe with Pydantic validation
- ✅ Clean, maintainable code
- ✅ Portable - works anywhere Python runs

**Development time:** Hours, not days
**Dependencies:** Python + Pydantic
**Complexity:** Minimal
