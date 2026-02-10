# skills/cli-parser-validation.md

## Skill: CLI Parser Validation with Ground Truth Comparison

### Purpose
Validate tree-sitter CLI parsers by comparing extracted data against authoritative sources (pathlib for filesystem tools, API responses for status commands, etc.). Focus on structural correctness, field extraction accuracy, and edge case handling.

---

## Core Testing Strategy

### Three-Layer Validation

**Layer 1: Grammar correctness (tree-sitter corpus tests)**
- Validates grammar rules in isolation
- Ensures no ERROR nodes on known-good input
- Fast feedback loop (< 1 second)

**Layer 2: Field extraction accuracy (unit tests)**
- Parse sample input → extract fields → compare to expected
- Tests wrapper extraction logic
- Medium feedback loop (< 5 seconds)

**Layer 3: End-to-end correctness (integration tests)**
- Generate real data → run CLI → parse output → compare to ground truth
- Validates entire pipeline
- Slow feedback loop (5-30 seconds)

---

## Ground Truth Sources by CLI Tool Type

### Filesystem Tools (lsd, ls, tree)

**Ground truth:** pathlib + os.stat()

```python
from pathlib import Path
import stat

def extract_ground_truth(directory: Path) -> list[dict]:
    """Extract authoritative filesystem metadata"""
    entries = []
    
    for path in directory.iterdir():
        st = path.stat(follow_symlinks=False)
        
        entry = {
            "name": path.name,
            "type": get_file_type(st.st_mode),
            "size_bytes": st.st_size,
            "permissions": stat.filemode(st.st_mode),
            "is_symlink": path.is_symlink(),
            "mtime": st.st_mtime,
        }
        
        if path.is_symlink():
            entry["link_target"] = str(path.readlink())
        
        entries.append(entry)
    
    return sorted(entries, key=lambda e: e["name"])

def get_file_type(mode: int) -> str:
    if stat.S_ISDIR(mode): return "directory"
    if stat.S_ISLNK(mode): return "symlink"
    if stat.S_ISREG(mode): return "file"
    if stat.S_ISBLK(mode): return "block_device"
    if stat.S_ISCHR(mode): return "char_device"
    if stat.S_ISFIFO(mode): return "fifo"
    if stat.S_ISSOCK(mode): return "socket"
    return "unknown"
```

### Process Tools (ps, top, htop)

**Ground truth:** /proc filesystem (Linux)

```python
from pathlib import Path

def extract_process_info(pid: int) -> dict:
    """Extract process info from /proc"""
    proc_dir = Path(f"/proc/{pid}")
    
    # Read status file
    status = {}
    with open(proc_dir / "status") as f:
        for line in f:
            key, value = line.split(":", 1)
            status[key.strip()] = value.strip()
    
    # Read cmdline
    with open(proc_dir / "cmdline") as f:
        cmdline = f.read().replace('\x00', ' ').strip()
    
    return {
        "pid": pid,
        "name": status["Name"],
        "state": status["State"],
        "ppid": int(status["PPid"]),
        "threads": int(status["Threads"]),
        "cmdline": cmdline,
    }
```

### Network Tools (ss, netstat, lsof)

**Ground truth:** /proc/net/* files or direct syscalls

```python
def extract_tcp_connections() -> list[dict]:
    """Parse /proc/net/tcp for connections"""
    connections = []
    
    with open("/proc/net/tcp") as f:
        next(f)  # Skip header
        for line in f:
            parts = line.split()
            
            local_addr, local_port = parse_address(parts[1])
            remote_addr, remote_port = parse_address(parts[2])
            
            connections.append({
                "local_addr": local_addr,
                "local_port": local_port,
                "remote_addr": remote_addr,
                "remote_port": remote_port,
                "state": TCP_STATES[int(parts[3], 16)],
            })
    
    return connections
```

### Kubernetes Tools (kubectl)

**Ground truth:** Kubernetes API

```python
from kubernetes import client, config

def extract_pod_info(namespace: str) -> list[dict]:
    """Query k8s API for pod metadata"""
    config.load_kube_config()
    v1 = client.CoreV1Api()
    
    pods = v1.list_namespaced_pod(namespace)
    
    return [{
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "status": pod.status.phase,
        "restarts": sum(cs.restart_count for cs in pod.status.container_statuses or []),
        "age_seconds": (datetime.now() - pod.metadata.creation_timestamp).total_seconds(),
    } for pod in pods.items]
```

---

## Test Fixture Generation

### Filesystem Fixture Generator

```python
from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel
import random
import string

class FileFixtureConfig(BaseModel):
    dirs: int = 5
    files: int = 10
    symlinks: int = 3
    file_size_range: tuple[int, int] = (1024, 1024*1024)
    include_spaces: bool = True
    include_special_chars: bool = True

def generate_filesystem_fixture(root: Path, config: FileFixtureConfig) -> None:
    """Generate test filesystem with varied file types"""
    root.mkdir(parents=True, exist_ok=True)
    
    # Generate directories
    for i in range(config.dirs):
        name = f"dir_{i:03d}"
        if config.include_spaces and i % 2 == 0:
            name = f"dir {i:03d}"
        (root / name).mkdir(exist_ok=True)
    
    # Generate files with random sizes
    for i in range(config.files):
        name = f"file_{i:03d}.txt"
        if config.include_special_chars and i % 3 == 0:
            name = f"file_(special)_{i}.txt"
        
        file_path = root / name
        size = random.randint(*config.file_size_range)
        file_path.write_bytes(random.randbytes(size))
    
    # Generate symlinks
    files = [f for f in root.iterdir() if f.is_file()]
    for i in range(min(config.symlinks, len(files))):
        target = files[i]
        link_name = f"link_{i:03d}"
        link_path = root / link_name
        link_path.symlink_to(target)
    
    # Generate edge cases
    (root / "empty_file").touch()
    (root / "file with many    spaces.txt").write_text("content")
    (root / "unicode_🔥_file.txt").write_text("emoji content")
```

### Property-Based Test Generator

```python
from hypothesis import given, strategies as st

@given(
    num_files=st.integers(min_value=1, max_value=100),
    num_dirs=st.integers(min_value=0, max_value=20),
    file_sizes=st.lists(st.integers(min_value=0, max_value=10*1024), min_size=1),
)
def test_lsd_parsing_property_based(tmp_path, num_files, num_dirs, file_sizes):
    """Property: parser extracts correct number of entries"""
    # Generate fixture
    for i in range(num_dirs):
        (tmp_path / f"dir{i}").mkdir()
    
    for i, size in enumerate(file_sizes[:num_files]):
        (tmp_path / f"file{i}").write_bytes(b"x" * size)
    
    # Extract ground truth
    pathlib_count = len(list(tmp_path.iterdir()))
    
    # Parse with lsd-json
    lsd_output = subprocess.run(["lsd", "--long", str(tmp_path)], capture_output=True)
    parsed = subprocess.run(["lsd-json"], input=lsd_output.stdout, capture_output=True)
    
    entries = extract_file_entries(json.loads(parsed.stdout))
    lsd_count = len(entries)
    
    # Property: counts must match
    assert lsd_count == pathlib_count
```

---

## Comparison Strategies

### Exact Match (Strict)

**Use case:** MVP acceptance criteria, high-confidence validation

```python
def compare_exact(pathlib_data: list[dict], parsed_data: list[dict]) -> ComparisonResult:
    """Compare with zero tolerance for differences"""
    
    if len(pathlib_data) != len(parsed_data):
        return ComparisonResult(
            success=False,
            error=f"Count mismatch: {len(pathlib_data)} vs {len(parsed_data)}"
        )
    
    mismatches = []
    for p, l in zip(pathlib_data, parsed_data):
        # Compare each field exactly
        for field in ["name", "permissions", "size_bytes"]:
            if p.get(field) != l.get(field):
                mismatches.append({
                    "file": p["name"],
                    "field": field,
                    "expected": p.get(field),
                    "actual": l.get(field),
                })
    
    return ComparisonResult(
        success=len(mismatches) == 0,
        total_comparisons=len(pathlib_data),
        mismatches=mismatches,
    )
```

### Normalized Match (Flexible)

**Use case:** Handle format variations, unit conversions

```python
def compare_normalized(pathlib_data: list[dict], parsed_data: list[dict]) -> ComparisonResult:
    """Compare with normalization for known format differences"""
    
    mismatches = []
    for p, l in zip(pathlib_data, parsed_data):
        # Name: exact match required
        if p["name"] != l["name"]:
            mismatches.append({"file": p["name"], "field": "name"})
        
        # Size: normalize units
        p_size = p["size_bytes"]
        l_size = parse_size_with_unit(l["size_value"], l["size_unit"])
        
        # Allow 1KB rounding error (lsd displays rounded values)
        if abs(p_size - l_size) > 1024:
            mismatches.append({
                "file": p["name"],
                "field": "size",
                "expected": p_size,
                "actual": l_size,
                "diff": abs(p_size - l_size),
            })
        
        # Permissions: format may differ but represent same bits
        p_perms = normalize_permissions(p["permissions"])
        l_perms = normalize_permissions(l["permissions"])
        if p_perms != l_perms:
            mismatches.append({"file": p["name"], "field": "permissions"})
    
    return ComparisonResult(
        success=len(mismatches) == 0,
        mismatches=mismatches,
    )

def parse_size_with_unit(value: str, unit: str) -> int:
    """Convert human-readable size to bytes"""
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    return int(float(value) * multipliers[unit])

def normalize_permissions(perms: str) -> int:
    """Convert permission string to octal for comparison"""
    # "drwxr-xr-x" -> 0o755
    mode = 0
    for i, c in enumerate(perms[1:]):  # Skip file type
        if c != '-':
            mode |= (1 << (8 - i))
    return mode
```

### Structural Match (Loose)

**Use case:** Smoke tests, early development, exploratory testing

```python
def compare_structural(pathlib_data: list[dict], parsed_data: list[dict]) -> ComparisonResult:
    """Compare structure only - presence/absence, types"""
    
    # Count match?
    count_match = len(pathlib_data) == len(parsed_data)
    
    # Name sets match?
    pathlib_names = {e["name"] for e in pathlib_data}
    parsed_names = {e["name"] for e in parsed_data}
    
    missing = pathlib_names - parsed_names
    extra = parsed_names - pathlib_names
    
    # Type distribution match?
    pathlib_types = {e["type"] for e in pathlib_data}
    parsed_types = {e["type"] for e in parsed_data if "type" in e}
    
    return ComparisonResult(
        success=count_match and len(missing) == 0 and len(extra) == 0,
        details={
            "count_match": count_match,
            "missing_files": list(missing),
            "extra_files": list(extra),
            "type_coverage": len(parsed_types) / len(pathlib_types) if pathlib_types else 0,
        },
    )
```

---

## Test Implementation Patterns

### Pytest Fixture Pattern

```python
# tests/conftest.py
from __future__ import annotations

import pytest
from pathlib import Path
from pydantic import BaseModel

class TestFilesystem(BaseModel):
    root: Path
    expected_files: list[dict]
    config: FileFixtureConfig

@pytest.fixture
def test_fs(tmp_path) -> TestFilesystem:
    """Generate test filesystem and ground truth"""
    config = FileFixtureConfig(dirs=5, files=10, symlinks=3)
    generate_filesystem_fixture(tmp_path, config)
    
    # Extract ground truth immediately
    expected = extract_ground_truth(tmp_path)
    
    return TestFilesystem(
        root=tmp_path,
        expected_files=expected,
        config=config,
    )

# tests/test_correctness.py
def test_lsd_parsing_correctness(test_fs):
    """Validate lsd parsing against pathlib ground truth"""
    # Run lsd -> lsd-json pipeline
    parsed = run_lsd_pipeline(test_fs.root)
    
    # Compare
    result = compare_normalized(test_fs.expected_files, parsed)
    
    assert result.success, f"Mismatches: {result.mismatches}"
```

### Parameterized Test Pattern

```python
@pytest.mark.parametrize("config", [
    FileFixtureConfig(dirs=0, files=5, symlinks=0),   # Files only
    FileFixtureConfig(dirs=5, files=0, symlinks=0),   # Dirs only
    FileFixtureConfig(dirs=0, files=0, symlinks=5),   # Symlinks only
    FileFixtureConfig(dirs=10, files=20, symlinks=5), # Mixed
    FileFixtureConfig(include_spaces=True),           # Spaces in names
    FileFixtureConfig(include_special_chars=True),    # Special chars
])
def test_lsd_parsing_variants(tmp_path, config):
    """Test parsing across different filesystem configurations"""
    generate_filesystem_fixture(tmp_path, config)
    
    pathlib_data = extract_ground_truth(tmp_path)
    parsed_data = run_lsd_pipeline(tmp_path)
    
    result = compare_structural(pathlib_data, parsed_data)
    assert result.success
```

### Edge Case Test Pattern

```python
def test_lsd_parsing_edge_cases(tmp_path):
    """Test known problematic cases"""
    
    # Empty directory
    (tmp_path / "empty_dir").mkdir()
    
    # File with no extension
    (tmp_path / "README").write_text("content")
    
    # File with multiple dots
    (tmp_path / "archive.tar.gz").write_bytes(b"data")
    
    # File with leading dot (hidden)
    (tmp_path / ".hidden").write_text("secret")
    
    # Symlink to non-existent target (broken)
    (tmp_path / "broken_link").symlink_to("nonexistent")
    
    # Circular symlinks
    (tmp_path / "link_a").symlink_to(tmp_path / "link_b")
    (tmp_path / "link_b").symlink_to(tmp_path / "link_a")
    
    # Run parsing
    parsed_data = run_lsd_pipeline(tmp_path)
    
    # Verify all entries present (may have ERROR nodes)
    parsed_names = {e["name"] for e in parsed_data}
    assert "empty_dir" in parsed_names
    assert "README" in parsed_names
    assert "broken_link" in parsed_names
```

---

## Pipeline Execution Patterns

### Subprocess Wrapper

```python
from __future__ import annotations

import subprocess
import json
from pathlib import Path

def run_lsd_pipeline(directory: Path) -> list[dict]:
    """Execute lsd -> lsd-json pipeline, return parsed entries"""
    
    # Step 1: Run lsd
    lsd_result = subprocess.run(
        ["lsd", "--long", str(directory)],
        capture_output=True,
        text=True,
        check=True,
    )
    
    if lsd_result.returncode != 0:
        raise RuntimeError(f"lsd failed: {lsd_result.stderr}")
    
    # Step 2: Parse with lsd-json
    parse_result = subprocess.run(
        ["wrappers/lsd-json", "--include-text"],
        input=lsd_result.stdout,
        capture_output=True,
        text=True,
        check=True,
    )
    
    if parse_result.returncode != 0:
        raise RuntimeError(f"lsd-json failed: {parse_result.stderr}")
    
    # Step 3: Extract entries from AST
    ast = json.loads(parse_result.stdout)
    return extract_file_entries(ast)

def extract_file_entries(ast: dict) -> list[dict]:
    """Walk AST and extract file_entry nodes with fields"""
    entries = []
    
    def walk(node):
        if node.get("type") == "file_entry":
            entry = {}
            for child in node.get("children", []):
                field_type = child.get("type")
                field_text = child.get("text", "")
                
                if field_type == "name":
                    entry["name"] = field_text
                elif field_type == "permissions":
                    entry["permissions"] = field_text
                elif field_type == "size_value":
                    entry["size_value"] = field_text
                elif field_type == "size_unit":
                    entry["size_unit"] = field_text
            
            entries.append(entry)
        
        for child in node.get("children", []):
            walk(child)
    
    walk(ast)
    return sorted(entries, key=lambda e: e.get("name", ""))
```

### Error Handling in Pipeline

```python
def run_lsd_pipeline_safe(directory: Path) -> tuple[list[dict], list[str]]:
    """Run pipeline, collect errors instead of raising"""
    errors = []
    
    # Run lsd
    try:
        lsd_result = subprocess.run(
            ["lsd", "--long", str(directory)],
            capture_output=True,
            text=True,
        )
        if lsd_result.returncode != 0:
            errors.append(f"lsd exit code: {lsd_result.returncode}")
            return [], errors
    except FileNotFoundError:
        errors.append("lsd not found in PATH")
        return [], errors
    
    # Parse output
    try:
        parse_result = subprocess.run(
            ["wrappers/lsd-json"],
            input=lsd_result.stdout,
            capture_output=True,
            text=True,
        )
        if parse_result.returncode != 0:
            errors.append(f"lsd-json exit code: {parse_result.returncode}")
            return [], errors
    except FileNotFoundError:
        errors.append("lsd-json wrapper not found")
        return [], errors
    
    # Parse JSON
    try:
        ast = json.loads(parse_result.stdout)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON output: {e}")
        return [], errors
    
    # Extract entries
    entries = extract_file_entries(ast)
    
    # Check for ERROR nodes in AST
    if has_error_nodes(ast):
        errors.append("Parse tree contains ERROR nodes")
    
    return entries, errors

def has_error_nodes(ast: dict) -> bool:
    """Check if AST contains ERROR nodes"""
    if ast.get("type") == "ERROR":
        return True
    for child in ast.get("children", []):
        if has_error_nodes(child):
            return True
    return False
```

---

## Comparison Result Models

### Pydantic Models for Test Results

```python
from __future__ import annotations

from pydantic import BaseModel

class FieldMismatch(BaseModel):
    file: str
    field: str
    expected: str | int | float | None
    actual: str | int | float | None
    diff: int | float | None = None

class ComparisonResult(BaseModel):
    success: bool
    total_comparisons: int = 0
    mismatches: list[FieldMismatch] = []
    details: dict = {}
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        if self.success:
            return f"✓ All {self.total_comparisons} comparisons passed"
        
        lines = [
            f"✗ {len(self.mismatches)} mismatches out of {self.total_comparisons}",
            "",
            "Mismatches by field:",
        ]
        
        # Group by field
        by_field: dict[str, list] = {}
        for m in self.mismatches:
            by_field.setdefault(m.field, []).append(m)
        
        for field, mismatches in sorted(by_field.items()):
            lines.append(f"  {field}: {len(mismatches)} files")
            for m in mismatches[:3]:  # Show first 3
                lines.append(f"    - {m.file}: {m.expected} vs {m.actual}")
            if len(mismatches) > 3:
                lines.append(f"    ... and {len(mismatches) - 3} more")
        
        return "\n".join(lines)
```

---

## Reporting Patterns

### JSON Test Report

```python
def generate_test_report(results: list[ComparisonResult], output_path: Path) -> None:
    """Generate JSON report of all test results"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [r.model_dump() for r in results],
    }
    
    output_path.write_text(json.dumps(report, indent=2))
    print(f"Report written to {output_path}")
```

### Markdown Test Report

```python
def generate_markdown_report(results: list[ComparisonResult]) -> str:
    """Generate markdown-formatted test report"""
    lines = [
        "# Validation Test Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"**Total Tests:** {len(results)}",
        f"**Passed:** {sum(1 for r in results if r.success)}",
        f"**Failed:** {sum(1 for r in results if not r.success)}",
        "",
    ]
    
    if any(not r.success for r in results):
        lines.extend([
            "## Failures",
            "",
        ])
        
        for i, result in enumerate(r for r in results if not r.success):
            lines.append(f"### Test {i+1}")
            lines.append(result.summary())
            lines.append("")
    
    return "\n".join(lines)
```

---

## Anti-Patterns

### Anti-Pattern: Order-Dependent Comparison

**❌ Wrong:**
```python
for i, (p, l) in enumerate(zip(pathlib_data, lsd_data)):
    assert p["name"] == l["name"]  # Breaks if order differs
```

**✓ Correct:**
```python
# Sort both by name before comparison
pathlib_sorted = sorted(pathlib_data, key=lambda x: x["name"])
lsd_sorted = sorted(lsd_data, key=lambda x: x["name"])

for p, l in zip(pathlib_sorted, lsd_sorted):
    assert p["name"] == l["name"]
```

### Anti-Pattern: Brittle String Comparison

**❌ Wrong:**
```python
assert lsd_output == "drwxr-xr-x user group 4.0 KB Jan 15 10:30 dir"
```

**✓ Correct:**
```python
# Parse and extract semantic fields
entry = parse_lsd_entry(lsd_output)
assert entry["permissions"] == "drwxr-xr-x"
assert entry["name"] == "dir"
```

### Anti-Pattern: No Normalization

**❌ Wrong:**
```python
assert pathlib_size == lsd_size  # Pathlib is bytes, lsd is "4.0 KB"
```

**✓ Correct:**
```python
lsd_bytes = parse_size_with_unit(lsd_size_value, lsd_size_unit)
assert abs(pathlib_size - lsd_bytes) < 1024  # Allow rounding
```

### Anti-Pattern: Ignoring Edge Cases

**❌ Wrong:**
```python
# Test only with simple filenames
generate_filesystem_fixture(tmp_path, FileFixtureConfig())
```

**✓ Correct:**
```python
# Test with edge cases included
config = FileFixtureConfig(
    include_spaces=True,
    include_special_chars=True,
)
generate_filesystem_fixture(tmp_path, config)
```

---

## Performance Considerations

### Benchmark Comparison Operations

```python
import time

def benchmark_comparison(pathlib_data, parsed_data, num_runs=100):
    """Measure comparison performance"""
    
    start = time.time()
    for _ in range(num_runs):
        result = compare_normalized(pathlib_data, parsed_data)
    elapsed = time.time() - start
    
    print(f"Average comparison time: {elapsed / num_runs * 1000:.2f}ms")
    print(f"Entries per second: {len(pathlib_data) * num_runs / elapsed:.0f}")
```

### Caching Ground Truth

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def extract_ground_truth_cached(directory: Path) -> tuple[dict, ...]:
    """Cache ground truth extraction (immutable result)"""
    entries = extract_ground_truth(directory)
    # Return tuple for hashability
    return tuple(frozenset(e.items()) for e in entries)
```

---

## Validation Checklist

### Test Coverage

- [ ] Empty directories tested
- [ ] Files with spaces in names
- [ ] Symlinks (valid and broken)
- [ ] Special characters in names
- [ ] Unicode characters
- [ ] Very long filenames (>255 chars if supported)
- [ ] Hidden files (.dotfiles)
- [ ] Files with no extensions
- [ ] Nested directory structures

### Comparison Quality

- [ ] Name matching is case-sensitive
- [ ] Size comparison handles unit conversion
- [ ] Permission comparison is semantic (not string)
- [ ] Timestamp comparison allows reasonable tolerance
- [ ] Missing files are reported
- [ ] Extra files are reported
- [ ] Field-level mismatches are detailed

### Test Reliability

- [ ] Tests run in isolated environments (tmp_path)
- [ ] No race conditions in file generation
- [ ] No assumptions about execution order
- [ ] Error messages are actionable
- [ ] Test failures include reproduction steps

---

## References

### Python Standard Library

- pathlib documentation: https://docs.python.org/3/library/pathlib.html
- os.stat: https://docs.python.org/3/library/os.html#os.stat
- subprocess: https://docs.python.org/3/library/subprocess.html

### Testing Frameworks

- pytest: https://docs.pytest.org/
- hypothesis: https://hypothesis.readthedocs.io/ (property-based testing)

### Comparison Strategies

- difflib (detailed diffs): https://docs.python.org/3/library/difflib.html
- deepdiff (nested structure comparison): https://github.com/seperman/deepdiff
