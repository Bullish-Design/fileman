# AGENTS.md

## Project Context

**Purpose:** Build grammar-specific CLI parsers using tree-sitter that emit JSON ASTs. Each parser is a Python uv script wrapping a compiled tree-sitter grammar.

**MVP Target:** Parse `lsd --long` output, validate against pathlib filesystem queries, establish reusable pattern.

**Key Insight:** tree-sitter CLI is a development tool, not a pipeline component. This fills the gap for production CLI-to-JSON parsers.

---

## Repository Structure

```
grammars/tree-sitter-<lang>/
  grammar.js              # Syntax rules - source of truth
  src/parser.c            # Generated (never edit)
  test/corpus/*.txt       # Corpus tests

build/
  <lang>.so / .dylib      # Compiled grammars (gitignored)

wrappers/
  <lang>-json             # Generated uv scripts

tests/
  test_correctness.py     # Pytest integration tests

scripts/
  *.py                    # uv scripts for complex operations

test_files/               # Generated (gitignored)

Justfile                  # Build automation
devenv.nix                # Environment packages
pyproject.toml            # Python dependencies
```

---

## Development Workflow

### Standard Loop

```bash
# 1. Edit grammar
vim grammars/tree-sitter-lsd/grammar.js

# 2. Generate + compile
just grammar-generate lsd
just grammar-compile lsd

# 3. Test
just grammar-test lsd        # Corpus tests
just test-correctness         # Full integration

# 4. Manual check
just lsd-parse test_files/
```

### When to Rebuild

**Regenerate (tree-sitter generate):** Modified grammar.js
**Recompile (gcc):** After regeneration
**No rebuild:** Wrapper edits, test changes

---

## Essential Skills

Detailed patterns in separate skill documents:

- **`skills/treesitter-grammar.md`** - Grammar DSL, parsing patterns, corpus tests, debugging
- **`skills/devenv-justfile-integration.md`** - Justfile recipes, platform detection, uv script integration
- **`skills/cli-parser-validation.md`** - Test strategies, ground truth comparison, fixtures

---

## Common Tasks

### Add New Grammar Rule

1. Identify unparsed pattern in sample output
2. Write corpus test in `test/corpus/*.txt`
3. Add rule to `grammar.js`
4. Run `just grammar-test <lang>` - expect failure
5. Iterate until test passes
6. Run `just test-correctness` to check regressions

### Debug ERROR Nodes

1. Isolate input: `echo "problematic line" > debug.txt`
2. Parse: `tree-sitter parse debug.txt`
3. Identify ERROR location in tree
4. Check grammar rule at that position
5. Add explicit whitespace if needed
6. Add corpus test for the fix

### Add Field Extraction

1. Ensure grammar recognizes field (corpus test)
2. Test harness will extract from AST automatically
3. Add normalization if needed (pathlib vs CLI format)
4. Update comparison assertions

---

## Critical Pitfalls

### Grammar Anti-Patterns

**❌ Greedy regex before specific fields:**
```javascript
name: $ => /.*/,  // Eats everything, breaks parsing
```

**✓ Bounded capture:**
```javascript
name: $ => /[^\n]+/,  // Stop at newline
```

**❌ Missing explicit whitespace:**
```javascript
file_entry: $ => seq($.user, $.group),  // Fields merge
```

**✓ Explicit delimiters:**
```javascript
file_entry: $ => seq($.user, /\s+/, $.group),
```

**❌ Wrong choice order:**
```javascript
value: $ => choice(/[0-9]+/, /[0-9]+\.[0-9]+/),  // Float never matches
```

**✓ Specific first:**
```javascript
value: $ => choice(/[0-9]+\.[0-9]+/, /[0-9]+/),
```

### Test Anti-Patterns

**❌ Order-dependent comparison:**
```python
assert lsd_data[0]["name"] == pathlib_data[0].name  # Breaks if order differs
```

**✓ Sort before compare:**
```python
lsd_sorted = sorted(lsd_data, key=lambda x: x["name"])
pathlib_sorted = sorted(pathlib_data, key=lambda x: x.name)
```

**❌ Brittle string matching:**
```python
assert output == "exact string"  # Format changes break test
```

**✓ Semantic extraction:**
```python
entry = parse_entry(output)
assert entry["name"] == "expected"
```

### Build Anti-Patterns

**❌ Platform-specific hardcoding:**
```bash
gcc -shared ...  # Breaks on macOS
```

**✓ Platform detection:**
```make
shared_flag := if os() == "macos" { "-dynamiclib" } else { "-shared" }
```

---

## Justfile Quick Reference

```make
# Grammar operations
just grammar-generate LANG    # Run tree-sitter generate
just grammar-compile LANG     # Compile to .so/.dylib
just grammar-test LANG        # Run corpus tests

# Wrapper operations
just wrapper-generate LANG    # Create uv script

# Testing
just test-unit                # pytest unit tests
just test-correctness         # Integration tests
just test-all                 # Everything

# Development
just lsd-parse PATH           # Parse directory with lsd -> lsd-json
just clean                    # Remove build artifacts
just rebuild-all              # Clean + full rebuild
```

---

## MVP Acceptance Criteria

### Grammar

- [ ] Parses `lsd --long` without ERROR nodes
- [ ] Extracts permissions, size, name fields
- [ ] Handles symlinks with `->` notation
- [ ] Corpus tests cover edge cases
- [ ] `just grammar-test lsd` passes

### Wrapper

- [ ] Loads compiled grammar successfully
- [ ] Reads stdin, emits valid JSON
- [ ] `--pretty`, `--include-text`, `--max-text` flags work
- [ ] Exit codes correct (0 success, 2 errors)

### Testing

- [ ] Generates test filesystem (dirs, files, symlinks)
- [ ] Extracts pathlib ground truth
- [ ] Runs lsd → lsd-json pipeline
- [ ] Compares outputs, reports mismatches
- [ ] >95% accuracy on 100 generated files
- [ ] `just test-correctness` passes

### Build

- [ ] `devenv shell` builds project
- [ ] `just grammar-compile lsd` produces .so/.dylib
- [ ] Platform detection works (Linux/macOS)
- [ ] Clean build from scratch <30 seconds

---

## Corpus Test Format

```
==================
Test case name
==================

Input text
Exactly as it appears in CLI output

---

(expected_ast
  (node_type
    (child_node)))
```

**Critical:**
- Exactly 18 equals signs
- Two blank lines before test name
- Input ends at `---` line
- AST uses S-expression syntax
- Indentation matters for nested nodes

---

## Key Questions Before Starting

### Grammar Development

1. What is exact format being parsed? (get sample output)
2. What CLI flags are in scope?
3. What fields need extraction?
4. What is ground truth source for validation?

### During Development

1. Do corpus tests cover all grammar branches?
2. Are ERROR nodes appearing?
3. Does grammar handle whitespace explicitly?
4. Are field boundaries unambiguous?

### Before Declaring Complete

1. Does grammar parse 100% of test cases without ERROR?
2. Do tests achieve >95% accuracy?
3. Can someone clone and build without help?
4. Are acceptance criteria met?

---

## Success Criteria

**You're done when:**
- Grammar parses target format cleanly (no ERROR nodes)
- `just test-correctness` passes
- Fresh `devenv shell` builds everything
- False positive/negative rate <5%
- Documentation complete

**You're NOT done when:**
- Grammar "mostly works" (ERROR nodes present)
- Tests pass on toy examples but fail on real data
- Build requires manual steps
- Performance poor (>1s for 100 lines)

---

## Environment Setup

**devenv.nix provides:**
- tree-sitter (grammar generation)
- gcc/clang (compilation)
- python312 + uv
- just (task runner)
- lsd (target CLI)

**No manual installs needed.** All deps in devenv packages.

---

## References

### Documentation

- Tree-sitter: https://tree-sitter.github.io/tree-sitter/
- Justfile: https://just.systems/man/en/
- devenv.sh: https://devenv.sh/

### Example Grammars

- tree-sitter-json (simple, clean)
- tree-sitter-bash (complex, handles ambiguity)

### Project Files

- `CONCEPT_MVP_LSD.md` - Full specification
- `grammars/tree-sitter-lsd/grammar.js` - Grammar source
- `Justfile` - Build recipes
- `tests/test_correctness.py` - Validation logic
