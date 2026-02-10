# skills/devenv-justfile-integration.md

## Skill: devenv.nix + Justfile Build Orchestration

### Purpose
Coordinate tree-sitter grammar compilation, wrapper generation, and testing in reproducible devenv.sh environments using Justfiles as the build automation layer.

---

## Core Architecture

### Responsibility Split

**devenv.nix responsibilities:**
- Package installation (tree-sitter, compilers, Python, uv)
- Environment variable setup
- Task scheduling (on shell entry, pre-commit hooks)
- Command exposure to shell

**Justfile responsibilities:**
- Recipe definitions (discrete build steps)
- Cross-platform logic (OS detection)
- Dependency ordering between recipes
- Developer workflow commands

**Interaction pattern:**
```
User → devenv shell → devenv task → just recipe → uv script
```

---

## Justfile Patterns

### Platform Detection

```make
# Justfile

# Detect operating system
os_type := if os() == "macos" { "macos" } else if os() == "linux" { "linux" } else { "unknown" }

# Platform-specific extensions
lib_ext := if os_type == "macos" { "dylib" } else { "so" }

# Platform-specific compiler flags
shared_flag := if os_type == "macos" { "-dynamiclib" } else { "-shared" }

# Example usage
grammar-compile LANG:
    gcc {{shared_flag}} -fPIC -O2 \
      grammars/tree-sitter-{{LANG}}/src/parser.c \
      -o build/{{LANG}}.{{lib_ext}}
```

**Rationale:** Justfile handles platform detection at build-time, eliminating need for shell script conditionals.

### Variable Definitions

```make
# Directories
grammars_dir := "grammars"
build_dir := "build"
wrappers_dir := "wrappers"
test_dir := "test_files"

# Tools
python := "uv run python"
pytest := "uv run pytest"

# Compiler settings
cc := env_var_or_default("CC", "gcc")
cflags := "-fPIC -O2 -std=c11"
```

**Usage:**
```make
grammar-compile LANG:
    {{cc}} {{cflags}} {{shared_flag}} \
      {{grammars_dir}}/tree-sitter-{{LANG}}/src/parser.c \
      -o {{build_dir}}/{{LANG}}.{{lib_ext}}
```

### Recipe Dependencies

```make
# Explicit dependency chain
grammar-compile LANG: (grammar-generate LANG)
    # Compile grammar (generate must run first)

wrapper-generate LANG: (grammar-compile LANG)
    # Generate wrapper (compile must run first)

test-correctness: (wrapper-generate "lsd")
    # Run tests (wrapper must exist first)

# Run multiple recipes in order
build-all: (grammar-compile "lsd") (wrapper-generate "lsd")
    @echo "Build complete"
```

**Key:** Dependencies in parentheses before recipe body.

### Default Recipe

```make
# Show available recipes when user runs `just`
default:
    @just --list
```

### Multi-Line Recipes

```make
# Use shebang for complex logic
grammar-compile LANG:
    #!/usr/bin/env bash
    set -euo pipefail
    
    GRAMMAR_DIR="{{grammars_dir}}/tree-sitter-{{LANG}}"
    OUTPUT="{{build_dir}}/{{LANG}}.{{lib_ext}}"
    
    # Check for scanner file
    if [ -f "$GRAMMAR_DIR/src/scanner.c" ]; then
        SCANNER="$GRAMMAR_DIR/src/scanner.c"
    else
        SCANNER=""
    fi
    
    # Compile
    {{cc}} {{shared_flag}} {{cflags}} \
      "$GRAMMAR_DIR/src/parser.c" \
      $SCANNER \
      -o "$OUTPUT"
    
    echo "Compiled: $OUTPUT"
```

**When to use:**
- Complex conditionals
- Multiple commands with error handling
- Need bash features (test, loops, etc.)

### Recipe Parameters

```make
# Required parameter
grammar-generate LANG:
    cd {{grammars_dir}}/tree-sitter-{{LANG}} && tree-sitter generate

# Optional parameter with default
test-parse LANG="lsd" FILE="samples/test.txt":
    tree-sitter parse -t {{LANG}} {{FILE}}

# Multiple parameters
compare-output LANG SOURCE TARGET:
    diff <(cat {{SOURCE}} | {{wrappers_dir}}/{{LANG}}-json) {{TARGET}}
```

### Calling uv Scripts

```make
# Direct invocation
generate-test-files:
    {{python}} scripts/generate_test_files.py --output {{test_dir}}

# With arguments
compare-outputs LANG:
    {{python}} scripts/compare_outputs.py \
      --lang {{LANG}} \
      --test-dir {{test_dir}} \
      --verbose

# Pytest execution
test-unit:
    {{pytest}} tests/ -v

test-integration:
    {{pytest}} tests/test_correctness.py -v -s
```

### Suppressing Command Echo

```make
# Show command (default)
loud:
    echo "This command is visible"

# Suppress echo with @
quiet:
    @echo "Only output is visible, not the command"

# Useful for clean output
status:
    @echo "Grammar: $(ls build/*.so 2>/dev/null | wc -l) compiled"
    @echo "Wrappers: $(ls wrappers/*-json 2>/dev/null | wc -l) generated"
```

---

## devenv.nix Integration

### Package Installation

```nix
{
  packages = [
    # Tree-sitter toolchain
    pkgs.tree-sitter
    
    # Compilers
    pkgs.gcc           # Linux C compiler
    pkgs.clang         # macOS compatibility
    
    # Python ecosystem
    pkgs.python312
    pkgs.uv
    
    # Build tools
    pkgs.just
    
    # CLI tools to parse
    pkgs.lsd
  ];
}
```

### Task Definitions

```nix
{
  tasks = {
    # Auto-build on shell entry
    "build:grammars" = {
      exec = "just grammar-compile lsd";
      before = ["devenv:enterShell"];
    };
    
    # Generate wrappers after grammars
    "build:wrappers" = {
      exec = "just wrapper-generate lsd";
      after = ["build:grammars"];
    };
    
    # Manual test execution
    "test:unit" = {
      exec = "just test-unit";
    };
    
    "test:correctness" = {
      exec = "just test-correctness";
    };
  };
}
```

**Task execution:**
```bash
# Automatic (before shell entry)
devenv shell  # Runs build:grammars automatically

# Manual
devenv task run test:unit
```

### Script Exposure

```nix
{
  scripts = {
    # Expose generated wrapper
    lsd-json.exec = "wrappers/lsd-json";
    
    # Convenience commands (delegate to Just)
    lsd-parse.exec = ''
      lsd --long "$@" | wrappers/lsd-json --pretty --include-text
    '';
    
    # Development workflows
    grammar-dev.exec = "just watch-grammar lsd";
    rebuild-all.exec = "just clean && just build-all";
    
    # Testing shortcuts
    test-quick.exec = "just test-unit";
    test-full.exec = "just test-all";
  };
}
```

### Environment Variables

```nix
{
  env = {
    # Project root (useful in scripts)
    PROJECT_ROOT = "$(pwd)";
    
    # Grammar build settings
    TREE_SITTER_GRAMMAR_PATH = "./build";
    
    # Compiler preferences
    CC = "gcc";
    CFLAGS = "-O2 -fPIC";
  };
}
```

**Access in Justfile:**
```make
project_root := env_var("PROJECT_ROOT")
grammar_path := env_var("TREE_SITTER_GRAMMAR_PATH")
```

---

## Common Workflows

### Grammar Development Loop

**Justfile recipes:**
```make
# Watch and rebuild on change
watch-grammar LANG:
    #!/usr/bin/env bash
    while true; do
        inotifywait -e modify {{grammars_dir}}/tree-sitter-{{LANG}}/grammar.js
        just grammar-generate {{LANG}}
        just grammar-compile {{LANG}}
        echo "Rebuilt {{LANG}} grammar"
    done

# Quick test cycle
grammar-dev LANG:
    @just grammar-generate {{LANG}}
    @just grammar-compile {{LANG}}
    @just grammar-test {{LANG}}
    @echo "Grammar {{LANG}} validated"

# Test with sample
test-parse LANG:
    @echo "Testing {{LANG}} grammar..."
    @tree-sitter parse -t {{LANG}} samples/{{LANG}}_sample.txt
```

### Clean Build

```make
# Remove all generated files
clean:
    @echo "Cleaning build artifacts..."
    @rm -rf {{build_dir}}/*
    @rm -rf {{wrappers_dir}}/*
    @rm -rf {{test_dir}}/*
    @find {{grammars_dir}} -name "src" -type d -exec rm -rf {} + 2>/dev/null || true
    @echo "Clean complete"

# Full rebuild from scratch
rebuild-all: clean
    @just grammar-generate lsd
    @just grammar-compile lsd
    @just wrapper-generate lsd
    @echo "Full rebuild complete"
```

### Testing Workflows

```make
# Generate test fixtures
test-setup:
    {{python}} scripts/generate_test_files.py \
      --output {{test_dir}} \
      --dirs 5 \
      --files 10 \
      --symlinks 3

# Run correctness tests
test-correctness: test-setup (wrapper-generate "lsd")
    {{pytest}} tests/test_correctness.py -v

# Run all tests
test-all: test-unit test-correctness
    @echo "All tests passed"

# Quick feedback loop
test-quick:
    {{pytest}} tests/test_grammar.py -v --tb=short
```

### Manual Verification

```make
# Parse lsd output with pretty printing
lsd-demo:
    @lsd --long {{test_dir}} | {{wrappers_dir}}/lsd-json --pretty --include-text

# Compare outputs side-by-side
lsd-compare:
    @echo "=== Pathlib ground truth ==="
    @{{python}} scripts/extract_pathlib_data.py {{test_dir}}
    @echo ""
    @echo "=== Tree-sitter parsed ==="
    @lsd --long {{test_dir}} | {{wrappers_dir}}/lsd-json --include-text | \
      {{python}} scripts/extract_treesitter_data.py
```

---

## Advanced Patterns

### Conditional Execution

```make
# Only compile if source changed
grammar-compile-if-needed LANG:
    #!/usr/bin/env bash
    GRAMMAR="{{grammars_dir}}/tree-sitter-{{LANG}}/grammar.js"
    OUTPUT="{{build_dir}}/{{LANG}}.{{lib_ext}}"
    
    if [ ! -f "$OUTPUT" ] || [ "$GRAMMAR" -nt "$OUTPUT" ]; then
        just grammar-compile {{LANG}}
    else
        echo "{{LANG}} grammar up to date"
    fi
```

### Parallel Execution

```make
# Compile multiple grammars in parallel
build-all-parallel:
    @echo "Building grammars in parallel..."
    @just grammar-compile lsd &
    @just grammar-compile kubectl &
    @just grammar-compile ps &
    @wait
    @echo "All grammars compiled"
```

**Note:** Use with caution - parallel just recipes can conflict with filesystem writes.

### Error Handling

```make
# Continue on error
grammar-test-all:
    -just grammar-test lsd
    -just grammar-test kubectl
    @echo "Testing complete (some may have failed)"

# Stop on first error (default behavior)
build-strict: (grammar-compile "lsd") (grammar-compile "kubectl")
    @echo "Strict build passed"
```

### Dynamic Recipe Generation

```make
# List of all grammars
grammars := "lsd kubectl ps"

# Generate test recipe for each
test-grammar LANG:
    @tree-sitter test -d {{grammars_dir}}/tree-sitter-{{LANG}}

# Test all grammars
test-all-grammars:
    #!/usr/bin/env bash
    for lang in {{grammars}}; do
        echo "Testing $lang..."
        just test-grammar $lang
    done
```

---

## Environment Setup Patterns

### Python Dependencies

**Option 1: Project-level pyproject.toml**
```toml
# pyproject.toml
[project]
name = "lsd-json"
version = "0.1.0"
dependencies = [
    "tree-sitter>=0.21.0",
    "pytest>=7.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Justfile usage:**
```make
# Install deps
install:
    uv pip install -e .

# Run tests with project deps
test-unit: install
    uv run pytest tests/
```

**Option 2: Inline uv script dependencies**
```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = ["tree-sitter>=0.21.0"]
# ///

# Script automatically installs tree-sitter when run
```

**Justfile usage:**
```make
# No explicit install needed
test-unit:
    uv run scripts/test_wrapper.py
```

**Recommendation:** Use Option 2 for scripts, Option 1 for pytest test suite.

### Path Management

```make
# Set paths relative to Justfile location
root_dir := justfile_directory()
build_dir := root_dir + "/build"
grammars_dir := root_dir + "/grammars"

# Use absolute paths in recipes
grammar-compile LANG:
    cd {{root_dir}} && \
    gcc -shared -fPIC \
      {{grammars_dir}}/tree-sitter-{{LANG}}/src/parser.c \
      -o {{build_dir}}/{{LANG}}.{{lib_ext}}
```

**Rationale:** Recipes work regardless of invocation directory.

---

## Integration with Git Hooks (via devenv)

### Pre-commit Hook

**devenv.nix:**
```nix
{
  pre-commit.hooks = {
    # Format code before commit
    black.enable = true;
    
    # Run grammar tests
    grammar-test = {
      enable = true;
      name = "Grammar tests";
      entry = "just grammar-test lsd";
      pass_filenames = false;
    };
    
    # Validate corpus tests
    corpus-test = {
      enable = true;
      name = "Corpus tests";
      entry = "just test-corpus";
      files = "\\.txt$";
    };
  };
}
```

**Justfile recipes:**
```make
# Quick pre-commit validation
pre-commit:
    @just grammar-test lsd
    @just test-unit
    @echo "Pre-commit checks passed"
```

---

## Debugging Recipes

### Verbose Mode

```make
# Normal mode
grammar-compile LANG:
    @gcc -shared ... -o {{build_dir}}/{{LANG}}.{{lib_ext}}

# Debug mode - show all commands
grammar-compile-verbose LANG:
    gcc -shared -fPIC -O2 -v \
      {{grammars_dir}}/tree-sitter-{{LANG}}/src/parser.c \
      -o {{build_dir}}/{{LANG}}.{{lib_ext}}
```

**Usage:** `just grammar-compile-verbose lsd`

### Dry Run

```make
# Show what would be executed
dry-run LANG:
    @echo "Would execute:"
    @echo "  just grammar-generate {{LANG}}"
    @echo "  just grammar-compile {{LANG}}"
    @echo "  just wrapper-generate {{LANG}}"
```

### Recipe Introspection

```make
# List all recipes with descriptions
help:
    @just --list --unsorted

# Show recipe definition
show-recipe RECIPE:
    @just --show {{RECIPE}}

# Evaluate variable
show-var VAR:
    @just --evaluate {{VAR}}
```

**Usage:**
```bash
just show-recipe grammar-compile
just show-var build_dir
```

---

## Common Pitfalls

### Pitfall: Incorrect Working Directory

**Problem:**
```make
# Recipe assumes cwd is project root
grammar-generate LANG:
    cd grammars/tree-sitter-{{LANG}} && tree-sitter generate
```

**Issue:** Fails if user runs `just` from subdirectory.

**Solution:**
```make
grammar-generate LANG:
    cd {{justfile_directory()}}/grammars/tree-sitter-{{LANG}} && tree-sitter generate
```

### Pitfall: Recipe Ordering Ambiguity

**Problem:**
```make
# Which order do these run?
build-all: grammar-compile wrapper-generate test-correctness
```

**Issue:** Just executes dependencies in parallel by default.

**Solution:**
```make
# Explicit dependency chain
build-all: (grammar-compile "lsd")
    @just wrapper-generate lsd
    @just test-correctness
```

### Pitfall: Platform-Specific Commands

**Problem:**
```make
watch-grammar LANG:
    inotifywait -e modify {{grammars_dir}}/tree-sitter-{{LANG}}/grammar.js
```

**Issue:** `inotifywait` not available on macOS.

**Solution:**
```make
watch-grammar LANG:
    #!/usr/bin/env bash
    if command -v inotifywait &> /dev/null; then
        inotifywait -e modify {{grammars_dir}}/tree-sitter-{{LANG}}/grammar.js
    elif command -v fswatch &> /dev/null; then
        fswatch -o {{grammars_dir}}/tree-sitter-{{LANG}}/grammar.js
    else
        echo "No file watcher available"
        exit 1
    fi
```

### Pitfall: Recipe Parameter Quoting

**Problem:**
```make
test-file FILE:
    echo {{FILE}} > /tmp/test.txt  # Breaks with spaces in filename
```

**Solution:**
```make
test-file FILE:
    echo "{{FILE}}" > /tmp/test.txt  # Proper quoting
```

---

## Validation Checklist

### Justfile Quality

- [ ] All recipes have explicit dependencies
- [ ] Platform-specific logic uses `os()` function
- [ ] Multi-line recipes use `#!/usr/bin/env bash`
- [ ] Variables defined at top of file
- [ ] Default recipe shows help/list
- [ ] Recipe names follow `action-target` convention
- [ ] No hardcoded absolute paths
- [ ] Error messages are clear

### devenv.nix Quality

- [ ] All required packages declared
- [ ] Tasks have clear names with `:` separator
- [ ] Task dependencies use `before`/`after`
- [ ] Scripts delegate to Just recipes (not inline bash)
- [ ] Environment variables set for common paths
- [ ] Pre-commit hooks reference Just recipes

### Integration Quality

- [ ] Fresh `devenv shell` builds project
- [ ] All Just recipes work from any directory
- [ ] Recipe dependencies prevent partial builds
- [ ] Clean recipe removes all generated files
- [ ] Test recipes can run independently

---

## References

### Just Documentation

- Official manual: https://just.systems/man/en/
- Command line options: `just --help`
- Recipe introspection: `just --list`, `just --show RECIPE`

### devenv.nix Documentation

- Official guide: https://devenv.sh/
- Tasks: https://devenv.sh/tasks/
- Scripts: https://devenv.sh/scripts/
- Pre-commit: https://devenv.sh/pre-commit-hooks/

### Example Justfiles

Study these open-source projects:
- ripgrep: Complex multi-platform builds
- deno: Extensive testing recipes
- zellij: Clean task organization
