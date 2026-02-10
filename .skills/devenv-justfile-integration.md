# .skills/devenv-justfile-integration.md

## Skill: devenv + Justfile Integration (Simplified)

### Purpose
Configure devenv to import pre-built parser and use Justfile for simple task automation. No build orchestration needed!

---

## Core Architecture (Simplified)

### Responsibility Split

**devenv.yaml responsibilities:**
- Import pre-built parser module
- No build tasks needed

**devenv.nix responsibilities:**
- Package installation (lsd, python, uv, just)
- Command exposure to shell
- No compilation or generation tasks

**Justfile responsibilities:**
- Simple wrapper commands
- Usage examples
- Validation helpers

**No build steps!** Everything is pre-built and imported.

---

## devenv Configuration

### devenv.yaml - Parser Import

```yaml
# yaml-language-server: $schema=https://devenv.sh/devenv.schema.json
imports:
  - path/to/lsd-parser  # Pre-built parser module
```

**That's it!** Parser is imported and ready to use.

### devenv.nix - Packages

```nix
{ pkgs, ... }:
{
  packages = with pkgs; [
    lsd           # CLI tool we're wrapping
    just          # Task runner
    python312     # For wrapper script
    uv            # Python package runner
    jq            # JSON validation
  ];

  scripts = {
    # Expose wrapper command
    lsd-json.exec = "uv run scripts/lsd-json";

    # Convenience command
    lsd-parse.exec = ''
      lsd --long "$@" | lsd-json
    '';

    # Help
    fileman-help.exec = ''
      echo "Fileman lsd-json wrapper"
      echo "Commands:"
      echo "  just lsd-parse <path>"
      echo "  just demo <path>"
      echo "  just test-json-valid <path>"
    '';
  };
}
```

---

## Justfile Patterns (Simplified)

### Basic Usage Commands

```make
# Justfile

# Default - show help
default:
    @just --list

# Parse a directory with lsd
lsd-parse PATH=".":
    lsd --long {{PATH}} | lsd-json

# Pretty print JSON output
demo PATH=".":
    lsd --long {{PATH}} | lsd-json | jq .

# Validate JSON output
test-json-valid PATH=".":
    @lsd --long {{PATH}} | lsd-json | jq empty
    @echo "✓ JSON is valid"

# Count entries
count PATH=".":
    @lsd --long {{PATH}} | lsd-json | jq '.entries | length'

# Show just filenames
names PATH=".":
    @lsd --long {{PATH}} | lsd-json | jq -r '.entries[].name'
```

**No build recipes!** Just usage commands.

### Variable Definitions

```make
# Simple variables
python := "uv run python"

# No build directories needed!
# No compiler settings needed!
# No platform detection needed!
```

---

## Common Workflows (Simplified)

### Daily Usage

```bash
# Enter shell (parser auto-imported)
devenv shell

# Use the wrapper
just lsd-parse /tmp

# Pretty output
just demo /home/user

# Validate
just test-json-valid .
```

### Testing

```bash
# Manual testing on various directories
just lsd-parse /tmp
just lsd-parse /home
just lsd-parse .

# Check JSON validity
just test-json-valid /tmp
```

**No test generation needed!** Use real directories.

---

## Justfile Quick Reference

```make
# Usage commands
just lsd-parse PATH     # Parse directory
just demo PATH          # Pretty print output
just test-json-valid    # Validate JSON
just count PATH         # Count entries
just names PATH         # List filenames

# No build commands needed!
```

---

## Common Pitfalls (Simplified)

### Pitfall: Wrong Import Path

**Problem:**
```yaml
imports:
  - nonexistent/parser  # Wrong path
```

**Solution:**
```yaml
imports:
  - path/to/lsd-parser  # Correct path
```

### Pitfall: Missing Packages

**Problem:**
```nix
packages = [ pkgs.lsd ];  # Missing uv, python
```

**Solution:**
```nix
packages = with pkgs; [ lsd just python312 uv jq ];
```

### Pitfall: Hardcoded Paths

**Problem:**
```make
lsd-parse:
    lsd --long /tmp | /home/user/scripts/lsd-json  # Hardcoded
```

**Solution:**
```make
lsd-parse PATH=".":
    lsd --long {{PATH}} | lsd-json  # Use parameter
```

---

## Environment Setup

**devenv shell provides:**
- lsd command
- python312 + uv
- just
- jq
- Imported parser

**No manual setup needed!**

---

## Integration Checklist

### devenv.yaml
- [ ] Parser import path is correct
- [ ] No build tasks (not needed)

### devenv.nix
- [ ] Required packages declared
- [ ] Scripts expose commands
- [ ] No build tasks (not needed)

### Justfile
- [ ] Usage commands defined
- [ ] Parameters use {{variable}} syntax
- [ ] Commands use @echo for clean output
- [ ] Default recipe shows help

### Testing
- [ ] `devenv shell` loads without errors
- [ ] `just lsd-parse /tmp` works
- [ ] `just demo /tmp` produces pretty output
- [ ] `just test-json-valid` passes

---

## Example Complete Setup

### File: devenv.yaml
```yaml
imports:
  - path/to/lsd-parser
```

### File: devenv.nix
```nix
{ pkgs, ... }:
{
  packages = with pkgs; [
    lsd
    just
    python312
    uv
    jq
  ];

  scripts.lsd-json.exec = "uv run scripts/lsd-json";
}
```

### File: Justfile
```make
default:
    @just --list

lsd-parse PATH=".":
    lsd --long {{PATH}} | lsd-json

demo PATH=".":
    lsd --long {{PATH}} | lsd-json | jq .

test-json-valid PATH=".":
    @lsd --long {{PATH}} | lsd-json | jq empty
    @echo "✓ Valid JSON"
```

### File: scripts/lsd-json
```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///

import sys
import json
import subprocess
from imported_parser import parse_lsd_output

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    result = subprocess.run(
        ["lsd", "--long", path],
        capture_output=True,
        text=True,
        check=True
    )
    parsed = parse_lsd_output(result.stdout)
    print(json.dumps(parsed, indent=2))

if __name__ == "__main__":
    main()
```

**Total development time: 15 minutes!**

---

## Success Criteria

**You're done when:**
- `devenv shell` loads with no errors
- Parser is imported successfully
- `just lsd-parse /path` produces JSON
- Output can be piped to `jq`

**You're NOT done when:**
- Parser import fails
- Commands not available in shell
- JSON output is invalid

---

## Key Advantages

**This simplified approach:**
- ✅ No grammar compilation
- ✅ No build scripts
- ✅ No platform detection
- ✅ No complex task dependencies
- ✅ Just import and use!

**Setup time:** Minutes, not hours

---

## References

### Documentation
- Justfile: https://just.systems/man/en/
- devenv.sh: https://devenv.sh/
- devenv imports: https://devenv.sh/imports/
- lsd: https://github.com/lsd-rs/lsd

### Key Concepts
- **imports:** How devenv loads external modules
- **scripts:** How devenv exposes commands
- **just recipes:** Task automation commands

**No tree-sitter, gcc, or build tool documentation needed!**
