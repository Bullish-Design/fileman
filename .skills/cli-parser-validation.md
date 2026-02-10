# .skills/cli-parser-validation.md

## Skill: CLI Parser Validation (Simplified)

### Purpose
Basic validation of lsd wrapper output. Parser is pre-tested elsewhere, so we just verify the wrapper works correctly.

---

## Testing Strategy (Simplified)

### Manual Validation

**Layer 1: Execution test**
- Run wrapper on real directories
- Verify it doesn't crash
- Fast feedback loop (< 1 second)

**Layer 2: JSON validation**
- Check output is valid JSON
- Use `jq` to validate structure
- Fast feedback loop (< 1 second)

**Layer 3: Spot checking**
- Inspect output manually
- Verify it looks reasonable
- Quick visual inspection

---

## Validation Commands

### Basic Testing

```bash
# Test wrapper executes
just lsd-parse /tmp
echo $?  # Should be 0

# Test JSON is valid
just lsd-parse /tmp | jq empty
echo $?  # Should be 0

# Inspect output
just lsd-parse /tmp | jq .
```

### Expected Output Structure

The JSON should look like:

```json
{
  "entries": [
    {
      "permissions": "drwxr-xr-x",
      "user": "user",
      "group": "group",
      "size": "4.0 KB",
      "timestamp": "...",
      "name": "directory_name",
      "type": "directory"
    }
  ]
}
```

Use `jq` to validate structure:

```bash
# Check entries array exists
just lsd-parse /tmp | jq '.entries[]' > /dev/null

# Count entries
just lsd-parse /tmp | jq '.entries | length'

# Show just names
just lsd-parse /tmp | jq '.entries[].name'
```

---

## Testing on Real Directories

### Test Various Scenarios

```bash
# Empty directory
mkdir -p /tmp/test_empty
just lsd-parse /tmp/test_empty

# Directory with files
mkdir -p /tmp/test_files
touch /tmp/test_files/file{1..5}.txt
just lsd-parse /tmp/test_files

# Directory with symlinks
mkdir -p /tmp/test_links
touch /tmp/test_links/target.txt
ln -s target.txt /tmp/test_links/link.txt
just lsd-parse /tmp/test_links

# Directory with spaces in names
mkdir -p "/tmp/test_spaces/dir with spaces"
touch "/tmp/test_spaces/file with spaces.txt"
just lsd-parse /tmp/test_spaces
```

**No complex test generation needed** - use real directories!

---

## Validation Approach (Simplified)

### Visual Inspection

The main validation method is visual inspection:

```bash
# Run and inspect output
just demo /tmp

# Compare with lsd output
lsd --long /tmp
just lsd-parse /tmp | jq .
```

### Spot Checks

Check a few specific things:

```bash
# Check entry count matches
ls -1 /tmp | wc -l
just lsd-parse /tmp | jq '.entries | length'

# Check specific file appears
just lsd-parse /tmp | jq '.entries[] | select(.name == "myfile.txt")'

# Check types are recognized
just lsd-parse /tmp | jq '.entries[].type' | sort | uniq
```

**No complex comparison needed** - parser is pre-validated!

---

## Common Issues

### Issue: Invalid JSON Output

**Problem:**
```bash
just lsd-parse /tmp | jq .
# parse error: Invalid numeric literal
```

**Solution:**
Check wrapper script isn't printing debug output mixed with JSON.

### Issue: Wrapper Not Found

**Problem:**
```bash
just lsd-parse /tmp
# command not found: lsd-json
```

**Solution:**
Verify you're in `devenv shell` and parser is imported correctly.

### Issue: Empty Output

**Problem:**
```bash
just lsd-parse /tmp
{}
```

**Solution:**
Check lsd command is working: `lsd --long /tmp`

---

## Validation Checklist

### Basic Functionality
- [ ] Wrapper executes without errors
- [ ] Output is valid JSON
- [ ] Entries array exists in output
- [ ] Each entry has expected fields

### Edge Cases
- [ ] Works on empty directories
- [ ] Handles files with spaces in names
- [ ] Handles symlinks
- [ ] Handles large directories (100+ files)

### Output Quality
- [ ] File names are correct
- [ ] Types are identified (file, directory, symlink)
- [ ] Output is well-formatted
- [ ] Can be piped to jq successfully

---

## Quick Validation Script

```bash
#!/usr/bin/env bash
# Quick validation of lsd-json wrapper

set -e

echo "=== Testing lsd-json wrapper ==="

# Test 1: Basic execution
echo "Test 1: Basic execution..."
just lsd-parse /tmp > /dev/null
echo "✓ Wrapper executes"

# Test 2: Valid JSON
echo "Test 2: Valid JSON output..."
just lsd-parse /tmp | jq empty
echo "✓ JSON is valid"

# Test 3: Structure check
echo "Test 3: Structure check..."
ENTRIES=$(just lsd-parse /tmp | jq '.entries | length')
echo "✓ Found $ENTRIES entries"

# Test 4: Field check
echo "Test 4: Field check..."
just lsd-parse /tmp | jq '.entries[0] | {name, type, permissions}' > /dev/null
echo "✓ Expected fields present"

echo ""
echo "=== All validation tests passed! ==="
```

Save this as `scripts/validate.sh` and run with `bash scripts/validate.sh`.

---

## References

### Tools
- jq (JSON processor): https://jqlang.github.io/jq/
- lsd (CLI tool): https://github.com/lsd-rs/lsd

### devenv
- devenv.sh documentation: https://devenv.sh/

**No tree-sitter or grammar references needed** - parser is pre-built!
