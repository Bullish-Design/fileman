# AGENTS.md

## Project Context

**Purpose:** Simple wrapper around the `lsd` command that outputs parsed filetree information as JSON.

**MVP Target:** Import pre-built parser, wrap `lsd --long` output, emit JSON structure.

**Key Insight:** Parser is already built and tested elsewhere. We just import it via devenv.yaml and use it - no grammar development needed.

---

## Repository Structure (Simplified)

```
scripts/
  lsd-json                # Simple wrapper script

Justfile                  # Task automation
devenv.yaml               # Parser import
devenv.nix                # Package management
README.md
CONCEPT_MVP_LSD.md
AGENTS.md
```

**Much simpler!** No grammars/, build/, or wrappers/ directories needed.

---

## Development Workflow (Simplified)

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
just demo /path

# Validate JSON output
just test-json-valid
```

**No build steps!** Parser is pre-built and imported.

---

## Essential Skills

Detailed patterns in separate skill documents:

- **`.skills/devenv-justfile-integration.md`** - Justfile recipes, devenv configuration
- **`.skills/cli-parser-validation.md`** - Basic validation strategies

**Note:** No grammar development skills needed for this simplified MVP!

---

## Common Tasks (Simplified)

### Test the Wrapper

```bash
# Run on a directory
just lsd-parse /some/path

# Check JSON is valid
just test-json-valid /some/path

# Pretty print for inspection
just demo /some/path
```

### Update the Wrapper Script

If you need to modify output format:

1. Edit `scripts/lsd-json`
2. Test with `just lsd-parse`
3. Done!

**No parser/grammar modifications needed** - that's all handled in the imported module.

---

## Common Pitfalls (Simplified)

### Wrapper Script Issues

**❌ Not handling lsd errors:**
```python
result = subprocess.run(["lsd", "--long", path])  # Doesn't check for errors
```

**✓ Check return codes:**
```python
result = subprocess.run(["lsd", "--long", path], check=True)
```

**❌ Invalid JSON output:**
```python
print("entries:", json_data)  # Extra text breaks JSON
```

**✓ Clean JSON only:**
```python
print(json.dumps(json_data))  # Pure JSON output
```

### devenv Configuration

**❌ Missing parser import:**
```yaml
# imports not specified
```

**✓ Specify imports:**
```yaml
imports:
  - path/to/lsd-parser
```

---

## Justfile Quick Reference (Simplified)

```make
# Usage commands
just lsd-parse PATH           # Parse directory with lsd
just demo PATH                # Pretty print JSON output
just test-json-valid PATH     # Validate JSON output

# That's it! No build commands needed.
```

---

## MVP Acceptance Criteria (Simplified)

### Setup

- [ ] devenv.yaml imports parser successfully
- [ ] `devenv shell` loads without errors
- [ ] `lsd-json` command is available in shell

### Functionality

- [ ] Wrapper executes lsd and captures output
- [ ] Parser produces valid JSON
- [ ] JSON structure contains file entries
- [ ] Handles directories, files, and symlinks

### Usage

- [ ] `just lsd-parse /path` works on real directories
- [ ] JSON output can be piped to `jq`
- [ ] No manual configuration needed
- [ ] Works immediately after entering devenv shell

---

## Testing (Simplified)

Manual testing is sufficient for the MVP:

```bash
# Test on various directories
just lsd-parse /tmp
just lsd-parse /home/user
just lsd-parse .

# Verify JSON is valid
just test-json-valid /path

# Inspect output
just demo /path | jq .
```

**No corpus tests needed** - parser is pre-tested!

---

## Key Questions Before Starting

### Setup Questions

1. Is the parser import path correct in devenv.yaml?
2. Does `devenv shell` load successfully?
3. Is `lsd` command available?

### Implementation Questions

1. Does the wrapper script execute lsd correctly?
2. Is the imported parser being called properly?
3. Does the JSON output have the right structure?

### Before Declaring Complete

1. Does `just lsd-parse /path` work on real directories?
2. Is the JSON output valid (test with `jq`)?
3. Are acceptance criteria met?

---

## Success Criteria (Simplified)

**You're done when:**
- `devenv shell` loads with imported parser
- `just lsd-parse /path` produces valid JSON
- Output can be piped to `jq` successfully
- Works on real directories without errors

**You're NOT done when:**
- Parser import fails
- Wrapper script produces invalid JSON
- lsd command execution fails
- devenv shell has errors

---

## Environment Setup (Simplified)

**devenv.yaml provides:**
- Parser import (pre-built, ready to use)

**devenv.nix provides:**
- lsd (CLI tool)
- python312 + uv (for wrapper script)
- just (task runner)

**No manual installs or builds needed!** Everything is pre-configured.

---

## References

### Documentation

- Justfile: https://just.systems/man/en/
- devenv.sh: https://devenv.sh/
- lsd: https://github.com/lsd-rs/lsd

### Project Files

- `CONCEPT_MVP_LSD.md` - MVP specification
- `Justfile` - Task automation
- `devenv.yaml` - Parser import configuration
- `devenv.nix` - Package management
- `scripts/lsd-json` - Wrapper script

**Note:** No grammar or tree-sitter documentation needed for this simplified MVP!
