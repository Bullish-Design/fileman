# CONCEPT — `lsd-json` MVP (Simple Parser Import)

## Goal
Create a simple wrapper around the `lsd` command that outputs parsed filetree information as JSON. The parser has already been built and tested elsewhere - we simply import it via devenv.yaml and use it.

**MVP focus:** Import pre-built parser, wrap `lsd --long` output, emit JSON structure.

---

## Architecture

### Components
1. **devenv.yaml:** Import pre-built parser file
2. **devenv.nix:** Package management (lsd, dependencies)
3. **Simple wrapper script:** Execute lsd and format output as JSON
4. **Justfile:** Basic commands for usage and testing

### Data flow
```
lsd --long /path → parse with imported parser → emit JSON
```

### Simplification
This is a **minimal MVP**. The parser is:
- Already built elsewhere
- Imported via devenv.yaml
- Ready to use without custom development

---

## lsd Output Format

### Example (lsd --long)
```
drwxr-xr-x  user group 4.0 KB Fri Jan 15 10:30:45 2025 directory_name
-rw-r--r--  user group 1.2 MB Fri Jan 15 10:29:33 2025 file_name.txt
lrwxrwxrwx  user group   15 B  Fri Jan 15 10:31:02 2025 symlink -> target
```

### Target JSON Output
```json
{
  "entries": [
    {
      "permissions": "drwxr-xr-x",
      "user": "user",
      "group": "group",
      "size": "4.0 KB",
      "timestamp": "Fri Jan 15 10:30:45 2025",
      "name": "directory_name",
      "type": "directory"
    },
    {
      "permissions": "-rw-r--r--",
      "user": "user",
      "group": "group",
      "size": "1.2 MB",
      "timestamp": "Fri Jan 15 10:29:33 2025",
      "name": "file_name.txt",
      "type": "file"
    },
    {
      "permissions": "lrwxrwxrwx",
      "user": "user",
      "group": "group",
      "size": "15 B",
      "timestamp": "Fri Jan 15 10:31:02 2025",
      "name": "symlink",
      "target": "target",
      "type": "symlink"
    }
  ]
}
```

**MVP scope:** Parse `lsd --long` output using imported parser

---

## Parser Import

### devenv.yaml Configuration
The parser is imported via devenv.yaml:

```yaml
imports:
  - path/to/lsd-parser  # Pre-built parser module
```

**Key points:**
- Parser is already built and tested elsewhere
- No grammar development needed
- No compilation steps required
- Simply import and use

### Parser Interface
The imported parser provides:
- Function to parse lsd output string
- Returns JSON structure with file entries
- Handles all edge cases (spaces, symlinks, etc.)

---

## Testing Strategy (Simplified)

### Basic Validation
Simple test to verify the wrapper works:

```bash
# Run lsd-json on a test directory
just lsd-parse test_directory/

# Verify JSON output is valid
just test-json-valid
```

### Manual Testing
Test the wrapper by running it on real directories:

```bash
# Test on current directory
just lsd-parse .

# Test on specific path
just lsd-parse /tmp

# Verify output is valid JSON
just lsd-parse . | jq .
```

The parser handles all the complexity internally - no need for extensive test harnesses.

---

## Wrapper Implementation (Simplified)

### Simple wrapper script
The wrapper is minimal - it calls lsd and uses the imported parser:

```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = []  # Parser imported from devenv
# ///

import sys
import json
import subprocess
from imported_parser import parse_lsd_output  # From devenv import

def main():
    # Read path from args or use current directory
    path = sys.argv[1] if len(sys.argv) > 1 else "."

    # Run lsd --long
    result = subprocess.run(
        ["lsd", "--long", path],
        capture_output=True,
        text=True,
        check=True
    )

    # Parse with imported parser
    parsed = parse_lsd_output(result.stdout)

    # Output JSON
    print(json.dumps(parsed, indent=2))

if __name__ == "__main__":
    main()
```

**Key simplifications:**
- No grammar loading/compilation
- Parser imported from devenv module
- Just calls lsd and formats output

---

## devenv Configuration (Simplified)

### devenv.yaml - Import Parser
```yaml
imports:
  - path/to/lsd-parser  # Pre-built parser module
```

### devenv.nix - Package Management
```nix
{ pkgs, ... }:
{
  packages = with pkgs; [
    lsd           # CLI tool we're wrapping
    just          # Task runner
    python312     # For wrapper script
    uv            # Python package runner
  ];

  scripts = {
    lsd-json.exec = "uv run scripts/lsd-json";

    lsd-parse.exec = ''
      lsd --long "$@" | lsd-json
    '';
  };
}
```

**No build tasks needed!** The parser is pre-built and imported.

---

## Justfile Commands

### Simple task automation
```make
# Default - show help
default:
    @just --list

# Parse a directory with lsd
lsd-parse PATH=".":
    lsd --long {{PATH}} | lsd-json

# Validate JSON output
test-json-valid PATH=".":
    lsd --long {{PATH}} | lsd-json | jq empty

# Show pretty output
demo PATH=".":
    lsd --long {{PATH}} | lsd-json | jq .
```

**No build recipes needed** - parser is pre-built!

---

## Repository Structure (Simplified)

```
fileman/
  scripts/
    lsd-json                  # Simple wrapper script
  Justfile                    # Task automation
  devenv.yaml                 # Parser import
  devenv.nix                  # Package management
  README.md
  CONCEPT_MVP_LSD.md
```

**Much simpler!** No grammars/, build/, or complex test harness needed.

---

## Usage Workflow (Simplified)

### Setup
```bash
# 1. Enter devenv shell (imports parser automatically)
devenv shell

# 2. Ready to use!
just lsd-parse /some/path
```

### Usage
```bash
# Parse current directory
just lsd-parse

# Parse specific path
just lsd-parse /tmp

# Get pretty JSON output
just demo /home/user

# Validate JSON is well-formed
just test-json-valid
```

**No grammar development needed** - parser is imported ready-to-use!

---

## MVP Acceptance Criteria (Simplified)

### Setup
- [ ] devenv.yaml imports parser successfully
- [ ] devenv shell loads without errors
- [ ] lsd-json command is available

### Functionality
- [ ] Wrapper executes lsd and captures output
- [ ] Parser produces valid JSON
- [ ] JSON structure contains file entries
- [ ] Handles directories, files, and symlinks

### Usage
- [ ] `just lsd-parse /path` works on real directories
- [ ] JSON output can be piped to jq
- [ ] No manual configuration needed

---

## Future Enhancements

If needed later:
- Additional output formats (CSV, etc.)
- Filtering capabilities
- Recursive directory traversal
- Integration with other tools

But for MVP: **keep it simple!**

---

## Success Metrics

MVP is complete when:
1. devenv shell successfully imports parser
2. `just lsd-parse /path` produces valid JSON
3. Output can be processed with jq
4. Works on real directories without errors

---

## Key Advantage

**This simplified approach:**
- ✅ No grammar development needed
- ✅ No compilation steps
- ✅ No complex test harnesses
- ✅ Parser already tested elsewhere
- ✅ Just import and use!

**Development time:** Minutes, not days/weeks
