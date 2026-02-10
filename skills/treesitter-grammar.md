# skills/treesitter-grammar.md

## Skill: Tree-sitter Grammar Development for CLI Parsing

### Purpose
Develop custom tree-sitter grammars that parse CLI tool output (tables, logs, structured text) into semantic AST representations. Focus on deterministic, unambiguous grammars suitable for JSON extraction.

---

## Core Concepts

### Grammar.js Structure
```javascript
module.exports = grammar({
  name: 'language_name',
  
  extras: $ => [/\s/],  // Optional: tokens to skip (whitespace)
  
  rules: {
    source_file: $ => repeat($.line),  // Root rule
    
    _hidden_rule: $ => choice(/* ... */),  // Underscore prefix = not in AST
    
    visible_rule: $ => seq(
      $.field_a,
      $.field_b
    ),
    
    field_a: $ => /pattern/,
  }
});
```

**Key elements:**
- `name`: Language identifier (used when loading compiled grammar)
- `extras`: Tokens to automatically skip (usually whitespace)
- `rules`: Object mapping rule names to definitions
- Root rule (convention: `source_file`) is entry point

### Rule Types

**Terminal rules (regex):**
```javascript
number: $ => /[0-9]+/,
identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,
```

**Sequence (all must match in order):**
```javascript
assignment: $ => seq($.identifier, '=', $.value),
```

**Choice (any one alternative):**
```javascript
value: $ => choice($.number, $.string, $.boolean),
```

**Repetition:**
```javascript
list: $ => repeat($.item),        // Zero or more
list: $ => repeat1($.item),       // One or more
list: $ => optional($.item),      // Zero or one
```

**Precedence (resolve ambiguity):**
```javascript
expression: $ => choice(
  prec.left(1, seq($.expr, '+', $.expr)),  // Left-associative, precedence 1
  prec.left(2, seq($.expr, '*', $.expr)),  // Higher precedence wins
),
```

**Field naming (for queries):**
```javascript
assignment: $ => seq(
  field('left', $.identifier),
  '=',
  field('right', $.value)
),
```

---

## CLI Parsing Patterns

### Pattern: Fixed-Width Columnar Data

**Example:** `lsd --long` permissions column
```
drwxr-xr-x
-rw-r--r--
```

**Grammar:**
```javascript
permissions: $ => /[ldrwx-]{10}/,  // Exactly 10 characters
```

**Rationale:** CLI tools often use fixed-width fields for alignment. Regex with exact length is most reliable.

### Pattern: Whitespace-Delimited Fields

**Example:** lsd output
```
drwxr-xr-x  user  group  4.0 KB  Jan 15  dirname
```

**Grammar:**
```javascript
file_entry: $ => seq(
  $.permissions,
  /\s+/,              // Explicit whitespace requirement
  $.user,
  /\s+/,
  $.group,
  /\s+/,
  $.size,
  /\s+/,
  $.timestamp,
  /\s+/,
  $.name
),
```

**Critical:** Always match whitespace explicitly. If whitespace is in `extras`, it's skipped automatically, which breaks field boundaries.

**Alternative (if whitespace in extras):**
```javascript
file_entry: $ => seq(
  $.permissions,
  $.user,      // Whitespace auto-skipped between tokens
  $.group,
  // ...
),
```

### Pattern: Greedy End-of-Line Capture

**Problem:** Filenames can contain spaces
```
file name with spaces.txt
```

**Grammar:**
```javascript
name: $ => /[^\n]+/,  // Consume everything until newline
```

**Critical:** This must be the LAST field in a sequence. Placing it earlier will cause it to consume subsequent fields.

**Correct:**
```javascript
file_entry: $ => seq(
  $.permissions,
  $.size,
  $.name  // Last position - can consume rest of line
),
```

**Wrong:**
```javascript
file_entry: $ => seq(
  $.name,        // Would consume everything
  $.permissions  // Never reached
),
```

### Pattern: Optional Trailing Content

**Example:** Symlinks have optional `-> target`
```
file.txt
link -> target
```

**Grammar:**
```javascript
file_entry: $ => seq(
  $.name,
  optional($.symlink_target)
),

symlink_target: $ => seq('->', $.target_path),
target_path: $ => /[^\n]+/,
```

### Pattern: Field With Unit

**Example:** File sizes
```
1.2 MB
450 KB
15 B
```

**Grammar:**
```javascript
size: $ => seq(
  $.size_value,
  $.size_unit
),

size_value: $ => /[0-9]+\.?[0-9]*/,

size_unit: $ => choice('B', 'KB', 'MB', 'GB', 'TB'),
```

**Rationale:** Separate nodes for value and unit enables semantic queries.

### Pattern: Conditional Format

**Example:** Timestamps show time (recent) or year (old)
```
Jan 15 10:30:45
Jan 15  2023
```

**Grammar:**
```javascript
timestamp: $ => seq(
  $.month,
  $.day,
  $.time_or_year
),

time_or_year: $ => choice(
  /[0-9]{2}:[0-9]{2}:[0-9]{2}/,  // HH:MM:SS
  /[0-9]{4}/                     // YYYY
),
```

**Key:** Choice between distinct patterns. Tree-sitter picks first match.

### Pattern: Multi-Column Grid Layout

**Example:** Default `lsd` output (not --long)
```
file1.txt  file2.txt  file3.txt
dir1/      dir2/      dir3/
```

**Strategy 1: Parse as words**
```javascript
source_file: $ => repeat($.filename),
filename: $ => /[^\s]+/,  // Any non-whitespace sequence
```

**Strategy 2: Parse with explicit newlines**
```javascript
source_file: $ => repeat($.line),
line: $ => seq(repeat1($.filename), '\n'),
filename: $ => /[^\s\n]+/,
```

**Tradeoff:** Strategy 1 is simpler but loses row structure. Strategy 2 preserves rows but more complex.

---

## Grammar Development Workflow

### Step 1: Collect Sample Input

```bash
# Capture various CLI output modes
lsd --long > samples/lsd_long.txt
lsd --tree > samples/lsd_tree.txt
lsd > samples/lsd_grid.txt

# Include edge cases
touch "file with spaces.txt"
ln -s target link
lsd --long > samples/lsd_edge_cases.txt
```

### Step 2: Create Minimal Grammar

```javascript
// Start simple - recognize lines only
module.exports = grammar({
  name: 'lsd',
  
  rules: {
    source_file: $ => repeat($._line),
    _line: $ => choice(
      $.file_entry,
      '\n'  // Empty lines
    ),
    file_entry: $ => /[^\n]+/,  // Entire line as single token
  }
});
```

### Step 3: Test Minimal Grammar

```bash
cd grammars/tree-sitter-lsd
tree-sitter generate
tree-sitter parse ../../samples/lsd_long.txt
```

**Expected:** Clean parse tree with `file_entry` nodes (no ERROR nodes)

### Step 4: Add Field Recognition

```javascript
file_entry: $ => seq(
  $.permissions,
  /\s+/,
  $.rest_of_line  // Temporary placeholder
),

permissions: $ => /[ldrwx-]{10}/,
rest_of_line: $ => /[^\n]+/,
```

**Test:** `tree-sitter parse samples/lsd_long.txt`

### Step 5: Incrementally Add Fields

```javascript
file_entry: $ => seq(
  $.permissions,
  /\s+/,
  $.user,
  /\s+/,
  $.rest_of_line  // Still placeholder
),

user: $ => /[a-zA-Z0-9_-]+/,
rest_of_line: $ => /[^\n]+/,
```

**Pattern:** Add one field at a time, test after each addition.

### Step 6: Write Corpus Tests

```
==================
Basic file entry
==================

-rw-r--r-- user group 1.2 MB Jan 15 10:30 file.txt

---

(source_file
  (file_entry
    (permissions)
    (user)
    (group)
    (size
      (size_value)
      (size_unit))
    (timestamp
      (month)
      (day)
      (time_or_year))
    (name)))
```

**Run:** `tree-sitter test`

### Step 7: Handle ERROR Nodes

**Debug workflow:**
```bash
# Parse problematic input
echo "drwxr-xr-x user group 4.0 KB Jan 15 10:30 test" > debug.txt
tree-sitter parse debug.txt

# Look for (ERROR) nodes in output
# Identify which rule failed
# Add explicit whitespace or adjust regex
```

**Common causes:**
- Missing whitespace token
- Greedy regex consuming too much
- Ambiguous rules (need precedence)

### Step 8: Test Edge Cases

Add corpus tests for:
- Empty directories
- Symlinks with arrows
- Filenames with spaces
- Very long filenames
- Special characters (parentheses, brackets)
- Unicode characters

---

## Corpus Test Format

### Structure

```
==================
Test case name
==================

Input text exactly as CLI outputs it
Multiple lines are fine

---

(expected_ast
  (node_type
    (child_node)
    (another_child)))

==================
Next test
==================
```

### Critical Rules

1. **Exactly 18 equals signs** in separator line
2. **Two blank lines** before test name
3. **Input ends at `---` line** (three hyphens)
4. **Expected AST uses S-expression syntax**
5. **Indentation matters** - children indented under parents
6. **Named nodes only** - hidden rules (underscore prefix) don't appear

### Example: Complex Test

```
==================
Symlink with target
==================

lrwxrwxrwx user group 15 B Jan 15 10:31 link -> target_file

---

(source_file
  (file_entry
    (permissions)
    (user)
    (group)
    (size
      (size_value)
      (size_unit))
    (timestamp
      (month)
      (day)
      (time_or_year))
    (name)
    (symlink_target
      (target_path))))
```

### Test Execution

```bash
# Run all corpus tests
tree-sitter test

# Run specific test file
tree-sitter test test/corpus/basic.txt

# Verbose output
tree-sitter test --debug
```

---

## Common Pitfalls and Solutions

### Pitfall: Whitespace in `extras` Causes Field Merging

**Problem:**
```javascript
extras: $ => [/\s/],  // Auto-skip whitespace

rules: {
  file_entry: $ => seq($.user, $.group),  // No explicit whitespace
  user: $ => /[a-z]+/,
  group: $ => /[a-z]+/,
}
```

**Result:** Input `"john admin"` parses as single token (whitespace skipped between characters)

**Solution 1:** Remove whitespace from extras
```javascript
extras: $ => [],  // No auto-skipping

rules: {
  file_entry: $ => seq($.user, /\s+/, $.group),  // Explicit whitespace
}
```

**Solution 2:** Use word boundaries
```javascript
user: $ => /\b[a-z]+\b/,  // Word boundary ensures separation
```

### Pitfall: Greedy Regex Consuming Delimiters

**Problem:**
```javascript
name: $ => /.*/,  // Matches everything
symlink_target: $ => seq('->', /.*/),
```

**Result:** `name` consumes `->` arrow, symlink_target never matches

**Solution:** Use negated character class
```javascript
name: $ => /[^-\n]+/,  // Stop at dash or newline
// Or use lookahead
name: $ => /.*(?=\s*->|\s*$)/,
```

### Pitfall: Ambiguous Rules Without Precedence

**Problem:**
```javascript
value: $ => choice(
  /[0-9]+/,          // Integer
  /[0-9]+\.[0-9]+/   // Float - never reached because integer matches first
),
```

**Solution:** Order by specificity
```javascript
value: $ => choice(
  /[0-9]+\.[0-9]+/,  // Float first (more specific)
  /[0-9]+/           // Integer second
),
```

### Pitfall: Incorrect Corpus Test Formatting

**Problem:**
```
================== 
Test name          (wrong: extra space after equals)
==================
```

**Solution:** Exactly 18 equals, no trailing spaces

**Problem:**
```
---
(expected_ast     (wrong: no blank line before AST)
  (child))
```

**Solution:** Blank line between `---` and AST

### Pitfall: Hidden Rules in Expected AST

**Problem:**
```javascript
rules: {
  _line: $ => choice($.file_entry, '\n'),  // Hidden rule (underscore)
}

// Corpus test expects:
(source_file
  (_line            ← WRONG: hidden rules don't appear in AST
    (file_entry)))
```

**Solution:**
```
(source_file
  (file_entry))     ← CORRECT: only named nodes appear
```

---

## Advanced Techniques

### External Scanners

**Use case:** Lexical rules that can't be expressed in regex (context-sensitive tokens, indentation-based structure)

**Example:** Python's INDENT/DEDENT tokens

**Structure:**
```c
// src/scanner.c
#include <tree_sitter/parser.h>

enum TokenType {
  INDENT,
  DEDENT,
};

void *tree_sitter_language_external_scanner_create() { /* ... */ }
void tree_sitter_language_external_scanner_destroy(void *payload) { /* ... */ }
bool tree_sitter_language_external_scanner_scan(/* ... */) { /* ... */ }
```

**Grammar reference:**
```javascript
externals: $ => [
  $.indent,
  $.dedent,
],

rules: {
  block: $ => seq(
    $.indent,
    repeat($.statement),
    $.dedent
  ),
}
```

**When to use:** Only when regex rules are insufficient. External scanners add complexity.

### Dynamic Precedence

**Use case:** Resolve shift-reduce conflicts in LR parsing

**Example:**
```javascript
statement: $ => choice(
  prec.dynamic(1, $.if_statement),      // Prefer if statement
  prec.dynamic(0, $.expression_statement)
),
```

### Conflict Resolution

**View conflicts:**
```bash
tree-sitter generate  # Shows warnings about conflicts
```

**Types:**
- **Shift-reduce:** Parser unsure whether to consume token (shift) or reduce to rule
- **Reduce-reduce:** Multiple rules match, parser unsure which to choose

**Solutions:**
1. Add precedence (`prec()`, `prec.left()`, `prec.right()`)
2. Rewrite grammar to remove ambiguity
3. Use dynamic precedence for runtime resolution

---

## Validation Checklist

### Grammar Completeness

- [ ] All sample inputs parse without ERROR nodes
- [ ] Corpus tests cover all grammar rules
- [ ] Edge cases included in corpus (empty fields, special chars, unicode)
- [ ] `tree-sitter test` passes 100%

### Field Extraction

- [ ] Each semantic field is a named node (not hidden)
- [ ] Field boundaries are unambiguous (explicit whitespace or fixed-width)
- [ ] Optional fields use `optional()` wrapper
- [ ] Repeating structures use `repeat()` or `repeat1()`

### Error Handling

- [ ] Malformed lines don't break entire parse (use `choice($.valid_line, $.error_line)`)
- [ ] ERROR nodes are localized (one bad line doesn't poison rest)
- [ ] Error recovery allows parsing to continue

### Performance

- [ ] Grammar compiles in < 5 seconds
- [ ] Parsing 1000 lines takes < 100ms (measure with `time tree-sitter parse large_file.txt`)
- [ ] No exponential backtracking (test with deeply nested structures)

---

## Integration with Wrapper

### Loading Compiled Grammar (Python)

```python
from tree_sitter import Language, Parser

# Load shared library
language = Language("./build/lsd.so", "lsd")

# Create parser
parser = Parser()
parser.set_language(language)

# Parse input
tree = parser.parse(input_bytes)
```

### Extracting Fields from AST

```python
def extract_file_entries(tree):
    """Extract file_entry nodes from tree"""
    entries = []
    
    for node in tree.root_node.children:
        if node.type == "file_entry":
            entry = {}
            for child in node.children:
                if child.type == "name":
                    entry["name"] = child.text.decode('utf-8')
                elif child.type == "permissions":
                    entry["permissions"] = child.text.decode('utf-8')
                # ... extract other fields
            entries.append(entry)
    
    return entries
```

**Note:** For MVP, emit raw AST JSON. Custom extraction is optional optimization.

---

## Debugging Strategies

### Visualize Parse Tree

```bash
tree-sitter parse input.txt
```

Output shows tree structure with node types and positions.

### Highlight Errors

```bash
tree-sitter parse input.txt | grep ERROR
```

Shows lines with ERROR nodes.

### Test Single Line

```bash
echo "single problematic line" | tree-sitter parse -
```

Isolate failing case.

### Compare Expected vs Actual

```bash
tree-sitter test --debug
```

Shows diff between corpus expected and actual parse tree.

### Add Debug Print Statements (External Scanner)

```c
// In scanner.c
fprintf(stderr, "Token: %d, Char: %c\n", token_type, current_char);
```

---

## Resources

### Essential Reading

- Tree-sitter documentation: https://tree-sitter.github.io/tree-sitter/
- Grammar DSL reference: https://tree-sitter.github.io/tree-sitter/creating-parsers#the-grammar-dsl
- Parsing algorithm explanation: https://tree-sitter.github.io/tree-sitter/creating-parsers#the-grammar-dsl

### Example Grammars to Study

- **tree-sitter-json:** Simple, clean structure
- **tree-sitter-bash:** Handles complex quoting/escaping
- **tree-sitter-python:** Indentation-based (external scanner)
- **tree-sitter-regex:** Compact, focused grammar

### Common CLI Tools to Parse

- **Table formats:** ps, top, lsof, netstat, ss, df, du
- **Log formats:** systemd journals, Apache logs, syslog
- **Status outputs:** git status, kubectl get, docker ps
- **Configuration:** /etc/fstab, /etc/hosts, crontab

---

## Anti-Patterns Summary

**❌ Don't:**
- Write overly permissive regexes (`.*/` matches everything)
- Rely on implicit whitespace handling (specify explicitly)
- Place greedy rules before specific ones in `choice()`
- Manually edit generated `src/parser.c`
- Skip corpus tests ("it works in my manual test")
- Use external scanners for simple lexing

**✓ Do:**
- Start simple, add complexity incrementally
- Test after every grammar rule addition
- Write corpus tests for every rule
- Use explicit whitespace tokens
- Order `choice()` alternatives by specificity
- Validate with `tree-sitter test` before integration
