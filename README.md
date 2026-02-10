# README.md

# Fileman

Tree-sitter based CLI output parser. Converts `lsd` output to JSON ASTs.

## Usage

### Setup

```bash
devenv shell  # Installs dependencies, builds grammar, generates wrapper
```

### Parse lsd Output

```bash
# Pipe lsd output
lsd --long /path/to/dir | fileman-json

# Pretty print
lsd --long /path/to/dir | fileman-json --pretty

# Include node text
lsd --long /path/to/dir | fileman-json --pretty --include-text

# Truncate text fields
lsd --long /path/to/dir | fileman-json --include-text --max-text 100
```

### Development

```bash
# Rebuild grammar
just grammar-compile lsd

# Run tests
just test-correctness

# Manual verification
just lsd-parse test_files/
```

## Output Format

JSON tree-sitter AST with nodes:
- `type`: Node type (e.g., "file_entry", "permissions", "name")
- `start_byte`, `end_byte`: Byte offsets
- `start_point`, `end_point`: Line/column positions
- `children`: Nested nodes
- `text`: Node text (if `--include-text`)

## Flags

- `--pretty`: Pretty-print JSON
- `--include-text`: Include node text in output
- `--max-text N`: Truncate text to N bytes (default: 4096)
