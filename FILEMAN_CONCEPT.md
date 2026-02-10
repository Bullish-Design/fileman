# CONCEPT — `fileman` MVP (Tree-sitter Grammar Development)

## Goal
Build a custom tree-sitter grammar for `lsd` CLI output and a Python uv wrapper that emits JSON parse trees. Validate correctness by comparing tree-sitter extracted data against pathlib filesystem queries. This serves as both a working tool and a reference implementation for grammar-based CLI parsing.

**MVP focus:** Parse `lsd --long` output, extract file entries with semantic fields, verify against ground truth.

---

## Architecture

### Components
1. **tree-sitter-lsd:** Custom grammar for lsd table format
2. **fileman:** Python uv wrapper script loading compiled grammar
3. **test harness:** File generator + pathlib comparison validator
4. **devenv.nix:** Build tasks for grammar compilation, wrapper generation, testing

### Data flow
```
lsd --long /path | fileman --pretty
                   ↓
              tree-sitter parse
                   ↓
              JSON AST with file_entry nodes
                   ↓
              extract: name, size, permissions
                   ↓
              compare vs pathlib.Path().stat()
```

---

## lsd Output Format

### Example (lsd --long)
```
drwxr-xr-x  user group 4.0 KB Fri Jan 15 10:30:45 2025 directory_name
-rw-r--r--  user group 1.2 MB Fri Jan 15 10:29:33 2025 file_name.txt
lrwxrwxrwx  user group   15 B  Fri Jan 15 10:31:02 2025 symlink -> target
```

### Fields to parse
- **Permissions:** 10-character string (file type + user/group/other rwx)
- **Link count:** Numeric (often omitted in simpler lsd views)
- **User:** Username string
- **Group:** Group name string
- **Size:** Value + unit (bytes, KB, MB, GB)
- **Timestamp:** Month, day, time (or year if old)
- **Name:** Filename (may contain spaces, special characters)
- **Symlink target:** Optional `-> target` suffix

### Format variations to handle
- **Icons:** lsd may prefix entries with emoji/nerd-font icons
- **Color codes:** ANSI escape sequences in output (need stripping or parsing)
- **Grid layout:** Default lsd output is multi-column (NOT --long format)
- **Tree view:** lsd --tree adds tree-drawing characters

**MVP scope:** Parse `lsd --long` output only (single column, no icons, no colors)

---

## Grammar Design

### Node structure (tree-sitter-lsd/grammar.js)
```javascript
module.exports = grammar({
  name: 'lsd',
  
  rules: {
    source_file: $ => repeat($._line),
    
    _line: $ => choice(
      $.file_entry,
      $.error_line
    ),
    
    file_entry: $ => seq(
      $.permissions,
      $.user,
      $.group,
      $.size,
      $.timestamp,
      $.name,
      optional($.symlink_target)
    ),
    
    permissions: $ => /[ldrwx-]{10}/,
    user: $ => /[a-zA-Z0-9_-]+/,
    group: $ => /[a-zA-Z0-9_-]+/,
    
    size: $ => seq(
      $.size_value,
      $.size_unit
    ),
    size_value: $ => /[0-9]+\.?[0-9]*/,
    size_unit: $ => choice('B', 'KB', 'MB', 'GB', 'TB'),
    
    timestamp: $ => seq(
      $.month,
      $.day,
      $.time_or_year
    ),
    month: $ => choice('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'),
    day: $ => /[0-9]{1,2}/,
    time_or_year: $ => choice(
      /[0-9]{2}:[0-9]{2}:[0-9]{2}/,  // HH:MM:SS
      /[0-9]{4}/                     // YYYY
    ),
    
    name: $ => /[^\n]+/,  // Filename can contain spaces, consume to EOL
    
    symlink_target: $ => seq(
      '->',
      /[^\n]+/
    ),
    
    error_line: $ => /[^\n]+/  // Fallback for unparseable lines
  }
});
```

### Grammar refinements needed
- **Whitespace handling:** lsd uses variable spacing between columns
- **Field boundaries:** Permissions is fixed-width (10 chars), others are space-delimited
- **Name field ambiguity:** Must be last token (consumes rest of line including spaces)
- **Error recovery:** Handle malformed lines gracefully

### Grammar development workflow
1. Write initial grammar.js
2. Run `tree-sitter generate` to produce parser
3. Test with `tree-sitter parse examples/lsd_output.txt`
4. Iterate on grammar rules based on parse failures
5. Add corpus tests in `test/corpus/basic.txt`

---

## Test Strategy

### File structure generation
```python
# scripts/generate_test_files.py
from pathlib import Path
import random
import string

def create_test_structure(root: Path, config: dict):
    """
    Generate test filesystem:
    - config['dirs']: number of directories
    - config['files']: number of regular files
    - config['symlinks']: number of symlinks
    - config['file_sizes']: (min, max) bytes
    """
    # Create directories
    for i in range(config['dirs']):
        (root / f"dir_{i:03d}").mkdir(parents=True, exist_ok=True)
    
    # Create files with varied sizes
    for i in range(config['files']):
        file = root / f"file_{i:03d}.txt"
        size = random.randint(*config['file_sizes'])
        file.write_bytes(random.randbytes(size))
    
    # Create symlinks
    for i in range(config['symlinks']):
        target = root / f"file_{i:03d}.txt"
        link = root / f"link_{i:03d}"
        if target.exists():
            link.symlink_to(target)
```

### Ground truth extraction (pathlib)
```python
# scripts/extract_pathlib_data.py
from pathlib import Path
import json
import stat

def extract_file_data(path: Path) -> dict:
    """Extract metadata using pathlib/os.stat"""
    s = path.stat()
    
    return {
        "name": path.name,
        "type": get_file_type(s.st_mode),
        "size_bytes": s.st_size,
        "permissions": stat.filemode(s.st_mode),
        "user_id": s.st_uid,
        "group_id": s.st_gid,
        "mtime": s.st_mtime,
        "is_symlink": path.is_symlink()
    }

def get_file_type(mode: int) -> str:
    if stat.S_ISDIR(mode): return "directory"
    if stat.S_ISLNK(mode): return "symlink"
    if stat.S_ISREG(mode): return "file"
    return "other"

def scan_directory(root: Path) -> list[dict]:
    return sorted(
        [extract_file_data(p) for p in root.iterdir()],
        key=lambda x: x["name"]
    )
```

### Tree-sitter data extraction
```python
# scripts/extract_treesitter_data.py
import subprocess
import json

def extract_lsd_data(directory: Path) -> list[dict]:
    """Run lsd -> fileman pipeline, extract fields"""
    
    # Run lsd --long
    lsd_result = subprocess.run(
        ["lsd", "--long", str(directory)],
        capture_output=True,
        text=True,
        check=True
    )
    
    # Parse with fileman
    parse_result = subprocess.run(
        ["fileman", "--include-text"],
        input=lsd_result.stdout,
        capture_output=True,
        text=True,
        check=True
    )
    
    # Extract fields from AST
    ast = json.loads(parse_result.stdout)
    entries = []
    
    for file_entry_node in find_nodes(ast, "file_entry"):
        entry = {
            "name": extract_field(file_entry_node, "name"),
            "permissions": extract_field(file_entry_node, "permissions"),
            "size_value": extract_field(file_entry_node, "size_value"),
            "size_unit": extract_field(file_entry_node, "size_unit"),
            # ... other fields
        }
        entries.append(entry)
    
    return sorted(entries, key=lambda x: x["name"])
```

### Comparison logic
```python
# scripts/compare_outputs.py
def normalize_permissions(pathlib_mode: str, lsd_perms: str) -> tuple[str, str]:
    """
    pathlib: 'drwxr-xr-x' (from stat.filemode)
    lsd: 'drwxr-xr-x'
    Should be identical for --long output
    """
    return (pathlib_mode, lsd_perms)

def normalize_size(pathlib_bytes: int, lsd_value: str, lsd_unit: str) -> tuple[int, int]:
    """
    Convert lsd human-readable size to bytes for comparison
    """
    unit_multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }
    lsd_bytes = int(float(lsd_value) * unit_multipliers[lsd_unit])
    
    # Allow small rounding differences (lsd rounds for display)
    return (pathlib_bytes, lsd_bytes)

def compare_entries(pathlib_data: list[dict], lsd_data: list[dict]) -> dict:
    """
    Compare extracted data, return diff report
    """
    assert len(pathlib_data) == len(lsd_data), "Entry count mismatch"
    
    mismatches = []
    for p, l in zip(pathlib_data, lsd_data):
        assert p["name"] == l["name"], f"Name ordering mismatch: {p['name']} vs {l['name']}"
        
        # Compare permissions
        if p["permissions"] != l["permissions"]:
            mismatches.append({
                "file": p["name"],
                "field": "permissions",
                "pathlib": p["permissions"],
                "lsd": l["permissions"]
            })
        
        # Compare size (with tolerance)
        p_size, l_size = normalize_size(p["size_bytes"], l["size_value"], l["size_unit"])
        if abs(p_size - l_size) > 1024:  # Allow 1KB rounding difference
            mismatches.append({
                "file": p["name"],
                "field": "size",
                "pathlib": p_size,
                "lsd": l_size
            })
    
    return {
        "total_files": len(pathlib_data),
        "mismatches": mismatches,
        "success": len(mismatches) == 0
    }
```

### Test execution (devenv task)
```bash
# Run by devenv task "test:correctness"
pytest tests/test_correctness.py -v

# tests/test_correctness.py
def test_lsd_parsing_correctness(tmp_path):
    # Generate files
    create_test_structure(tmp_path, {
        'dirs': 5,
        'files': 10,
        'symlinks': 3,
        'file_sizes': (1024, 1024*1024)
    })
    
    # Extract via both methods
    pathlib_data = scan_directory(tmp_path)
    lsd_data = extract_lsd_data(tmp_path)
    
    # Compare
    result = compare_entries(pathlib_data, lsd_data)
    
    assert result["success"], f"Mismatches found: {result['mismatches']}"
```

---

## Python Wrapper Implementation

### File: fileman (uv script)
```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = ["tree-sitter>=0.21.0"]
# ///
# fileman

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from tree_sitter import Language, Parser

GRAMMAR_PATH = "./build/lsd.so"  # Embedded at generation time
LANGUAGE_NAME = "lsd"


def load_grammar() -> Language:
    """Load compiled tree-sitter grammar"""
    try:
        return Language(GRAMMAR_PATH, LANGUAGE_NAME)
    except Exception as e:
        print(f"Error loading grammar: {e}", file=sys.stderr)
        sys.exit(2)


def parse_stdin(parser: Parser, include_text: bool, max_text: int) -> dict:
    """Read stdin, parse with tree-sitter, return AST as dict"""
    source_bytes = sys.stdin.buffer.read()
    tree = parser.parse(source_bytes)
    return node_to_dict(tree.root_node, source_bytes, include_text, max_text)


def node_to_dict(node, source: bytes, include_text: bool, max_text: int) -> dict:
    """Convert tree-sitter node to JSON-serializable dict"""
    result = {
        "type": node.type,
        "named": node.is_named,
        "start_byte": node.start_byte,
        "end_byte": node.end_byte,
        "start_point": {"row": node.start_point[0], "column": node.start_point[1]},
        "end_point": {"row": node.end_point[0], "column": node.end_point[1]},
    }
    
    if include_text:
        text = source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')
        if len(text) > max_text:
            text = text[:max_text] + "..."
        result["text"] = text
    
    if node.child_count > 0:
        result["children"] = [
            node_to_dict(child, source, include_text, max_text) 
            for child in node.children
        ]
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Parse lsd output with tree-sitter")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--include-text", action="store_true", help="Include node text")
    parser.add_argument("--max-text", type=int, default=4096, help="Max text length per node")
    args = parser.parse_args()
    
    language = load_grammar()
    ts_parser = Parser()
    ts_parser.set_language(language)
    
    ast = parse_stdin(ts_parser, args.include_text, args.max_text)
    
    if args.pretty:
        print(json.dumps(ast, indent=2))
    else:
        print(json.dumps(ast))


if __name__ == "__main__":
    main()
```

---

## devenv.nix Integration

### Package installation
```nix
{
  packages = [
    pkgs.lsd          # CLI tool we're parsing
    pkgs.tree-sitter  # For grammar generation
    pkgs.gcc          # For compiling grammar
    pkgs.python312    # Runtime for uv scripts
    pkgs.uv           # Python package manager
  ];
}
```

### Tasks for grammar workflow
```nix
{
  tasks = {
    # Step 1: Clone grammar repo (if not vendored)
    "setup:grammar" = {
      exec = ''
        if [ ! -d grammars/tree-sitter-lsd ]; then
          mkdir -p grammars
          # For now, create empty grammar dir (we'll write grammar.js)
          mkdir -p grammars/tree-sitter-lsd/src
        fi
      '';
    };
    
    # Step 2: Generate parser from grammar.js
    "build:grammar:generate" = {
      exec = ''
        cd grammars/tree-sitter-lsd
        tree-sitter generate
      '';
      after = ["setup:grammar"];
    };
    
    # Step 3: Compile to shared library
    "build:grammar:compile" = {
      exec = ''
        bash scripts/build_grammar.sh \
          grammars/tree-sitter-lsd \
          build/lsd.so
      '';
      after = ["build:grammar:generate"];
    };
    
    # Step 4: Generate wrapper script
    "build:wrapper" = {
      exec = ''
        python scripts/make_wrapper.py \
          lsd \
          build/lsd.so \
          > wrappers/fileman
        chmod +x wrappers/fileman
      '';
      after = ["build:grammar:compile"];
    };
    
    # Test generation
    "test:generate-files" = {
      exec = ''
        python scripts/generate_test_files.py \
          --output test_files \
          --dirs 5 \
          --files 10 \
          --symlinks 3
      '';
    };
    
    # Correctness test
    "test:correctness" = {
      exec = "pytest tests/test_correctness.py -v";
      after = ["build:wrapper", "test:generate-files"];
    };
    
    # Manual verification
    "test:manual" = {
      exec = ''
        lsd --long test_files | wrappers/fileman --pretty --include-text
      '';
      after = ["build:wrapper", "test:generate-files"];
    };
  };
}
```

### Exposed commands
```nix
{
  scripts = {
    fileman.exec = "wrappers/fileman";
    
    # Convenience wrapper
    lsd-parse.exec = ''
      lsd --long "$@" | fileman --pretty --include-text
    '';
    
    # Full test cycle
    test-lsd.exec = ''
      devenv task run test:generate-files
      devenv task run test:correctness
    '';
  };
}
```

---

## Build Scripts

### scripts/build_grammar.sh
```bash
#!/usr/bin/env bash
# scripts/build_grammar.sh <grammar_dir> <output_so>

set -euo pipefail

GRAMMAR_DIR="$1"
OUTPUT_SO="$2"

if [ ! -d "$GRAMMAR_DIR/src" ]; then
    echo "Error: $GRAMMAR_DIR/src not found" >&2
    exit 1
fi

if [ ! -f "$GRAMMAR_DIR/src/parser.c" ]; then
    echo "Error: $GRAMMAR_DIR/src/parser.c not found. Run 'tree-sitter generate' first." >&2
    exit 1
fi

# Detect platform
case "$(uname -s)" in
    Linux*)
        EXT="so"
        FLAGS="-shared"
        ;;
    Darwin*)
        EXT="dylib"
        FLAGS="-dynamiclib"
        ;;
    *)
        echo "Unsupported platform: $(uname -s)" >&2
        exit 1
        ;;
esac

# Detect C++ scanner
if [ -f "$GRAMMAR_DIR/src/scanner.cc" ] || [ -f "$GRAMMAR_DIR/src/scanner.cpp" ]; then
    COMPILER="g++"
    SCANNER_SRC=$(ls "$GRAMMAR_DIR/src/scanner.c"* 2>/dev/null | head -1)
else
    COMPILER="gcc"
    SCANNER_SRC="$GRAMMAR_DIR/src/scanner.c"
fi

# Compile
echo "Compiling grammar: $GRAMMAR_DIR -> $OUTPUT_SO"
mkdir -p "$(dirname "$OUTPUT_SO")"

if [ -f "$SCANNER_SRC" ]; then
    $COMPILER $FLAGS -fPIC -O2 \
        -I"$GRAMMAR_DIR/src" \
        "$GRAMMAR_DIR/src/parser.c" \
        "$SCANNER_SRC" \
        -o "$OUTPUT_SO"
else
    $COMPILER $FLAGS -fPIC -O2 \
        -I"$GRAMMAR_DIR/src" \
        "$GRAMMAR_DIR/src/parser.c" \
        -o "$OUTPUT_SO"
fi

echo "Grammar compiled successfully: $OUTPUT_SO"
```

### scripts/make_wrapper.py
```python
#!/usr/bin/env python3
# scripts/make_wrapper.py <lang_name> <grammar_path>

import sys
from pathlib import Path

TEMPLATE = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = ["tree-sitter>=0.21.0"]
# ///
# {lang_name}-json

from __future__ import annotations

import sys
import json
import argparse
from tree_sitter import Language, Parser

GRAMMAR_PATH = "{grammar_path}"
LANGUAGE_NAME = "{lang_name}"

# ... [rest of wrapper code from above] ...
'''

def main():
    if len(sys.argv) != 3:
        print("Usage: make_wrapper.py <lang_name> <grammar_path>", file=sys.stderr)
        sys.exit(1)
    
    lang_name = sys.argv[1]
    grammar_path = sys.argv[2]
    
    # Verify grammar exists
    if not Path(grammar_path).exists():
        print(f"Error: Grammar not found: {grammar_path}", file=sys.stderr)
        sys.exit(1)
    
    # Generate wrapper
    wrapper_code = TEMPLATE.format(
        lang_name=lang_name,
        grammar_path=grammar_path
    )
    
    print(wrapper_code)

if __name__ == "__main__":
    main()
```

---

## Repository Structure

```
fileman/
  grammars/
    tree-sitter-lsd/
      grammar.js              # Our custom grammar
      src/
        parser.c              # Generated by tree-sitter
        tree_sitter/
          parser.h
      test/
        corpus/
          basic.txt           # Corpus tests for grammar
  build/
    lsd.so                    # Compiled grammar
  wrappers/
    fileman                  # Generated uv script
  scripts/
    build_grammar.sh          # Compile grammar to .so
    make_wrapper.py           # Generate uv wrapper script
    generate_test_files.py    # Create test filesystem
    extract_pathlib_data.py   # Ground truth extraction
    extract_treesitter_data.py # Parse lsd output
    compare_outputs.py        # Validation logic
  tests/
    test_correctness.py       # pytest test suite
  test_files/                 # Generated test data (gitignored)
  pyproject.toml
  devenv.nix
  CONCEPT_MVP_LSD.md
```

---

## Grammar Development Workflow

### Initial grammar creation
```bash
# 1. Create grammar directory
mkdir -p grammars/tree-sitter-lsd

# 2. Write grammar.js (see Grammar Design section)
vim grammars/tree-sitter-lsd/grammar.js

# 3. Generate parser
cd grammars/tree-sitter-lsd
tree-sitter generate

# 4. Test with sample input
echo "drwxr-xr-x user group 4.0 KB Jan 15 10:30 dirname" > sample.txt
tree-sitter parse sample.txt

# 5. Iterate on grammar based on parse tree
# Edit grammar.js, regenerate, retest
```

### Corpus test development
```
# grammars/tree-sitter-lsd/test/corpus/basic.txt

==================
Basic directory entry
==================

drwxr-xr-x user group 4.0 KB Jan 15 10:30 dirname

---

(source_file
  (file_entry
    (permissions)
    (user)
    (group)
    (size (size_value) (size_unit))
    (timestamp (month) (day) (time_or_year))
    (name)))

==================
File with symlink
==================

lrwxrwxrwx user group 15 B Jan 15 10:31 link -> target

---

(source_file
  (file_entry
    (permissions)
    (user)
    (group)
    (size (size_value) (size_unit))
    (timestamp (month) (day) (time_or_year))
    (name)
    (symlink_target)))
```

### Running corpus tests
```bash
cd grammars/tree-sitter-lsd
tree-sitter test

# Output shows pass/fail for each test case
```

---

## MVP Acceptance Criteria

### Grammar functionality
- [ ] Grammar parses `lsd --long` output without ERROR nodes
- [ ] Extracts permissions field correctly
- [ ] Extracts size value and unit
- [ ] Extracts filename (including spaces)
- [ ] Handles symlink arrow notation
- [ ] Corpus tests pass (10+ test cases covering edge cases)

### Wrapper functionality
- [ ] `fileman` loads compiled grammar successfully
- [ ] Reads stdin and parses without errors
- [ ] Emits valid JSON to stdout
- [ ] `--pretty` flag formats JSON correctly
- [ ] `--include-text` includes node text
- [ ] `--max-text` truncates long text fields

### Test harness
- [ ] Generates test filesystem (dirs, files, symlinks)
- [ ] Extracts pathlib metadata correctly
- [ ] Runs lsd → fileman pipeline
- [ ] Compares outputs and reports mismatches
- [ ] Zero false positives on 100 generated files
- [ ] Zero false negatives on 100 generated files

### Build workflow
- [ ] `devenv task run build:grammar:generate` succeeds
- [ ] `devenv task run build:grammar:compile` produces .so
- [ ] `devenv task run build:wrapper` creates executable script
- [ ] `devenv task run test:correctness` passes all tests
- [ ] Clean build from scratch takes < 30 seconds

### Integration
- [ ] `lsd --long /path | fileman --pretty` produces readable output
- [ ] devenv.nix exposes `fileman` command globally in shell
- [ ] No manual path configuration required (grammar path embedded)

---

## Deferred Features

### Grammar enhancements
- Icon/emoji parsing (lsd with nerd fonts)
- ANSI color code handling
- Grid layout parsing (multi-column default view)
- Tree view parsing (lsd --tree)
- Long format variations (lsd --blocks, --inode)

### Wrapper improvements
- `fileman run --` mode (execute lsd internally)
- `--fail-on-error` flag (exit 1 if ERROR nodes)
- `--query` mode (apply tree-sitter queries)
- Streaming parser (for very large listings)

### Test coverage
- Property-based testing (hypothesis)
- Fuzzing with generated lsd outputs
- Cross-platform testing (Linux, macOS)
- Different lsd versions compatibility
- Edge cases: Unicode filenames, special characters, very long names

### Tooling
- CI/CD pipeline for grammar updates
- Grammar version tracking
- Benchmark suite (parse performance)
- VSCode extension for grammar development

---

## Known Challenges

### Field boundary detection
**Problem:** lsd uses variable whitespace between columns
**Example:**
```
-rw-r--r-- shortname group 10 B  Jan 15 10:30 file.txt
-rw-r--r-- verylongusername group 10 B  Jan 15 10:30 file2.txt
```
User field width varies, making regex-based parsing fragile.

**Solutions:**
1. Use tree-sitter precedence rules (prefer longer matches)
2. Make whitespace token explicit, count delimiters
3. Leverage field ordering (permissions always first, name always last)

### Filename with spaces
**Problem:** Filename field must consume rest of line
**Example:** `file name with spaces.txt`

**Solution:** Define `name` rule as `/[^\n]+/` (greedy match to EOL)

### Size unit variations
**Problem:** lsd may use B, KB, MB, or adaptive units
**Example:**
```
1.2 MB
450 KB
15 B
```

**Solution:** Grammar defines all possible units, accept any

### Timestamp format ambiguity
**Problem:** Recent files show time, old files show year
**Examples:**
```
Jan 15 10:30:45  (recent)
Jan 15  2023     (old)
```

**Solution:** `time_or_year` rule with choice between time pattern and year pattern

### Symlink target parsing
**Problem:** Target may contain spaces or special characters
**Example:** `link -> target with spaces/path`

**Solution:** After `->` delimiter, consume to EOL (same as filename)

---

## Success Metrics

MVP is complete when:
1. Grammar correctly parses 100% of generated test cases (no ERROR nodes)
2. Wrapper extracts filenames with 100% accuracy vs pathlib
3. Permission strings match pathlib.stat() output exactly
4. Size comparisons within 1KB tolerance (rounding acceptable)
5. Build workflow is fully automated via devenv tasks
6. Test suite runs in < 10 seconds for 100 files
7. Documentation allows grammar modification by non-tree-sitter experts

---

## Next Steps After MVP

### Generalize pattern
1. Extract grammar-agnostic wrapper template
2. Create grammar development guide
3. Build library of common CLI grammars (ps, df, netstat, etc.)
4. Publish as reusable devenv module

### Performance optimization
1. Profile parsing for large outputs (1000+ lines)
2. Implement streaming parser if needed
3. Cache compiled grammars
4. Parallel parsing for multi-file inputs
