# LSD Validation Test Suite

This test suite validates that the `lsd` parser and `pathlib` collector produce equivalent data structures.

## Overview

The validation suite consists of:

1. **Pydantic Models** (`models.py`) - Data structures for file listings
2. **Pathlib Collector** (`pathlib_collector.py`) - Collects file data using Python's pathlib
3. **LSD Parser** (`lsd_parser.py`) - Parses `lsd --long` output
4. **Pytest Tests** (`test_validation.py`) - Validates equivalence

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│  Pathlib Collector  │         │    LSD Parser       │
│  (pathlib_collector │         │   (lsd_parser.py)   │
│        .py)         │         │                     │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           │ Uses pathlib                  │ Runs lsd --long
           │ to inspect                    │ and parses output
           │ filesystem                    │
           │                               │
           ▼                               ▼
    ┌─────────────────────────────────────────┐
    │        Pydantic Models (models.py)      │
    │  ┌─────────────────────────────────┐   │
    │  │ FileEntry                       │   │
    │  │  - permissions, user, group     │   │
    │  │  - size, timestamp, name        │   │
    │  │  - type, target                 │   │
    │  └─────────────────────────────────┘   │
    │  ┌─────────────────────────────────┐   │
    │  │ FileListings                    │   │
    │  │  - entries: list[FileEntry]     │   │
    │  └─────────────────────────────────┘   │
    └─────────────────────────────────────────┘
                       │
                       │ Both produce
                       │ identical JSON
                       ▼
            ┌──────────────────────┐
            │  Pytest Validation   │
            │ (test_validation.py) │
            │                      │
            │ ✓ Valid JSON         │
            │ ✓ Pydantic parses    │
            │ ✓ Equivalent data    │
            └──────────────────────┘
```

## Running the Tests

### Prerequisites

- Python 3.11+
- `uv` (for running scripts)
- `lsd` command installed
- `pytest` (installed via dependencies)

### Install Dependencies

```bash
# Using uv
uv pip install -e .

# Or using pip
pip install -e .
```

### Run Full Test Suite

```bash
# Run all tests
pytest test_validation.py -v

# Run specific test class
pytest test_validation.py::TestDataEquivalence -v

# Run with detailed output
pytest test_validation.py -vv
```

### Manual Testing

You can also run the scripts individually:

```bash
# Collect data using pathlib
python pathlib_collector.py /tmp > pathlib_output.json

# Parse lsd output
python lsd_parser.py /tmp > lsd_output.json

# Compare outputs
diff <(jq -S . pathlib_output.json) <(jq -S . lsd_output.json)
```

## Test Structure

### Test Classes

1. **TestJSONValidity** - Validates JSON output format
   - Both outputs produce valid JSON
   - JSON contains expected structure

2. **TestPydanticValidation** - Validates Pydantic model compatibility
   - Pathlib JSON loads into Pydantic models
   - LSD JSON loads into Pydantic models
   - All entries are valid FileEntry objects

3. **TestDataEquivalence** - Validates data equivalence
   - Same number of entries
   - Same filenames
   - Matching file types
   - Matching permissions
   - Matching symlink targets

4. **TestSpecificScenarios** - Tests edge cases
   - Files with spaces in names
   - Empty directories
   - Executable files

5. **TestFullEquivalence** - End-to-end validation
   - Complete models are equivalent

## Test Fixtures

- `test_directory` - Creates a temporary directory with:
  - Regular files
  - Directories
  - Symlinks
  - Files with spaces
  - Executable files

- `pathlib_json` - JSON output from pathlib collector
- `lsd_json` - JSON output from lsd parser

## What Gets Validated

For each file system entry, the tests verify:

- ✓ Permissions string (e.g., "drwxr-xr-x")
- ✓ User owner
- ✓ Group owner
- ✓ File type (file, directory, symlink)
- ✓ Filename
- ✓ Symlink target (for symlinks)

Note: Size and timestamp are collected but not strictly compared, as formatting may vary slightly between implementations.

## Expected Output

```
test_validation.py::TestJSONValidity::test_pathlib_produces_valid_json PASSED
test_validation.py::TestJSONValidity::test_lsd_produces_valid_json PASSED
test_validation.py::TestPydanticValidation::test_pathlib_json_loads_to_pydantic PASSED
test_validation.py::TestPydanticValidation::test_lsd_json_loads_to_pydantic PASSED
test_validation.py::TestPydanticValidation::test_both_have_file_entries PASSED
test_validation.py::TestDataEquivalence::test_same_number_of_entries PASSED
test_validation.py::TestDataEquivalence::test_same_filenames PASSED
test_validation.py::TestDataEquivalence::test_matching_file_types PASSED
test_validation.py::TestDataEquivalence::test_matching_permissions PASSED
test_validation.py::TestDataEquivalence::test_symlink_targets_match PASSED
test_validation.py::TestSpecificScenarios::test_handles_files_with_spaces PASSED
test_validation.py::TestSpecificScenarios::test_handles_empty_directories PASSED
test_validation.py::TestSpecificScenarios::test_handles_executable_files PASSED
test_validation.py::TestFullEquivalence::test_models_are_equivalent PASSED
```

## Troubleshooting

### lsd command not found

Install lsd:
```bash
# macOS
brew install lsd

# Linux (Debian/Ubuntu)
sudo apt install lsd

# Or using cargo
cargo install lsd
```

### Import errors

Ensure dependencies are installed:
```bash
uv pip install pydantic pytest
```

### Permission errors

Some tests require the ability to create symlinks and set file permissions. Run with appropriate permissions.
