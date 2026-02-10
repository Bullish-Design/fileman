"""Pytest validation suite for lsd parser and pathlib collector equivalence."""

import json
import subprocess
import tempfile
from pathlib import Path
import pytest
from models import FileEntry, FileListings


# Check if lsd is available
def is_lsd_available():
    """Check if lsd command is available."""
    try:
        subprocess.run(["lsd", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


LSD_AVAILABLE = is_lsd_available()
requires_lsd = pytest.mark.skipif(not LSD_AVAILABLE, reason="lsd command not installed")


@pytest.fixture
def test_directory(tmp_path):
    """Create a test directory with various file types for testing."""
    # Create directories
    (tmp_path / "empty_dir").mkdir()
    (tmp_path / "data").mkdir()

    # Create regular files
    (tmp_path / "README.md").write_text("# Test README\n")
    (tmp_path / "script.sh").write_text("#!/bin/bash\necho 'test'\n")
    (tmp_path / "data" / "config.json").write_text('{"key": "value"}\n')

    # Make script executable
    (tmp_path / "script.sh").chmod(0o755)

    # Create a symlink
    (tmp_path / "link_to_readme").symlink_to("README.md")

    # Create files with spaces in names
    (tmp_path / "file with spaces.txt").write_text("content\n")

    return tmp_path


@pytest.fixture
def pathlib_json(test_directory, tmp_path):
    """Generate JSON output from pathlib collector."""
    output_file = tmp_path / "pathlib_output.json"

    result = subprocess.run(
        ["python", "pathlib_collector.py", str(test_directory)],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).parent,
    )

    output_file.write_text(result.stdout)
    return output_file


@pytest.fixture
def lsd_json(test_directory, tmp_path):
    """Generate JSON output from lsd parser."""
    if not LSD_AVAILABLE:
        pytest.skip("lsd command not installed")

    output_file = tmp_path / "lsd_output.json"

    result = subprocess.run(
        ["python", "lsd_parser.py", str(test_directory)],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).parent,
    )

    output_file.write_text(result.stdout)
    return output_file


class TestJSONValidity:
    """Test that both outputs produce valid JSON."""

    def test_pathlib_produces_valid_json(self, pathlib_json):
        """Verify pathlib collector produces valid JSON."""
        with open(pathlib_json) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "entries" in data

    @requires_lsd
    def test_lsd_produces_valid_json(self, lsd_json):
        """Verify lsd parser produces valid JSON."""
        with open(lsd_json) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "entries" in data


class TestPydanticValidation:
    """Test that both JSONs can be loaded into Pydantic models."""

    def test_pathlib_json_loads_to_pydantic(self, pathlib_json):
        """Verify pathlib JSON can be parsed by Pydantic model."""
        with open(pathlib_json) as f:
            data = json.load(f)

        # This will raise ValidationError if invalid
        listings = FileListings(**data)
        assert isinstance(listings, FileListings)
        assert len(listings.entries) > 0

    @requires_lsd
    def test_lsd_json_loads_to_pydantic(self, lsd_json):
        """Verify lsd JSON can be parsed by Pydantic model."""
        with open(lsd_json) as f:
            data = json.load(f)

        # This will raise ValidationError if invalid
        listings = FileListings(**data)
        assert isinstance(listings, FileListings)
        assert len(listings.entries) > 0

    def test_pathlib_has_valid_file_entries(self, pathlib_json):
        """Verify pathlib output contains FileEntry objects."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        # Check all entries are valid FileEntry instances
        for entry in pathlib_data.entries:
            assert isinstance(entry, FileEntry)

    @requires_lsd
    def test_both_have_file_entries(self, pathlib_json, lsd_json):
        """Verify both outputs contain FileEntry objects."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        # Check all entries are valid FileEntry instances
        for entry in pathlib_data.entries:
            assert isinstance(entry, FileEntry)

        for entry in lsd_data.entries:
            assert isinstance(entry, FileEntry)


class TestDataEquivalence:
    """Test that both approaches produce equivalent data."""

    @requires_lsd
    def test_same_number_of_entries(self, pathlib_json, lsd_json):
        """Verify both outputs have the same number of entries."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        assert len(pathlib_data.entries) == len(lsd_data.entries)

    @requires_lsd
    def test_same_filenames(self, pathlib_json, lsd_json):
        """Verify both outputs contain the same filenames."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        pathlib_names = {entry.name for entry in pathlib_data.entries}
        lsd_names = {entry.name for entry in lsd_data.entries}

        assert pathlib_names == lsd_names

    @requires_lsd
    def test_matching_file_types(self, pathlib_json, lsd_json):
        """Verify file types match for each entry."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        # Create dictionaries keyed by name
        pathlib_by_name = {entry.name: entry for entry in pathlib_data.entries}
        lsd_by_name = {entry.name: entry for entry in lsd_data.entries}

        for name in pathlib_by_name:
            assert name in lsd_by_name
            assert pathlib_by_name[name].type == lsd_by_name[name].type

    @requires_lsd
    def test_matching_permissions(self, pathlib_json, lsd_json):
        """Verify permissions match for each entry."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        pathlib_by_name = {entry.name: entry for entry in pathlib_data.entries}
        lsd_by_name = {entry.name: entry for entry in lsd_data.entries}

        for name in pathlib_by_name:
            assert pathlib_by_name[name].permissions == lsd_by_name[name].permissions

    @requires_lsd
    def test_symlink_targets_match(self, pathlib_json, lsd_json):
        """Verify symlink targets match."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        pathlib_by_name = {entry.name: entry for entry in pathlib_data.entries}
        lsd_by_name = {entry.name: entry for entry in lsd_data.entries}

        # Find symlinks
        for name in pathlib_by_name:
            entry = pathlib_by_name[name]
            if entry.type == "symlink":
                assert lsd_by_name[name].type == "symlink"
                assert entry.target == lsd_by_name[name].target


class TestSpecificScenarios:
    """Test specific file system scenarios."""

    @requires_lsd
    def test_handles_files_with_spaces(self, pathlib_json, lsd_json):
        """Verify files with spaces in names are handled correctly."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        pathlib_names = {entry.name for entry in pathlib_data.entries}
        lsd_names = {entry.name for entry in lsd_data.entries}

        # Check that file with spaces exists in both
        assert "file with spaces.txt" in pathlib_names
        assert "file with spaces.txt" in lsd_names

    @requires_lsd
    def test_handles_empty_directories(self, pathlib_json, lsd_json):
        """Verify empty directories are detected."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        pathlib_by_name = {entry.name: entry for entry in pathlib_data.entries}
        lsd_by_name = {entry.name: entry for entry in lsd_data.entries}

        # Check empty_dir exists and is marked as directory
        assert "empty_dir" in pathlib_by_name
        assert pathlib_by_name["empty_dir"].type == "directory"
        assert "empty_dir" in lsd_by_name
        assert lsd_by_name["empty_dir"].type == "directory"

    @requires_lsd
    def test_handles_executable_files(self, pathlib_json, lsd_json):
        """Verify executable permissions are captured."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        pathlib_by_name = {entry.name: entry for entry in pathlib_data.entries}
        lsd_by_name = {entry.name: entry for entry in lsd_data.entries}

        # Check script.sh has execute permissions
        assert "script.sh" in pathlib_by_name
        script_perms = pathlib_by_name["script.sh"].permissions
        # Should have at least user execute permission
        assert "x" in script_perms

        assert lsd_by_name["script.sh"].permissions == script_perms


class TestFullEquivalence:
    """Test complete equivalence of both models."""

    @requires_lsd
    def test_models_are_equivalent(self, pathlib_json, lsd_json):
        """Verify the complete FileListings models are equivalent."""
        with open(pathlib_json) as f:
            pathlib_data = FileListings(**json.load(f))

        with open(lsd_json) as f:
            lsd_data = FileListings(**json.load(f))

        # Convert to dictionaries for comparison (excluding timestamps and sizes which may differ slightly)
        pathlib_by_name = {
            entry.name: {
                "permissions": entry.permissions,
                "user": entry.user,
                "group": entry.group,
                "type": entry.type,
                "target": entry.target,
            }
            for entry in pathlib_data.entries
        }

        lsd_by_name = {
            entry.name: {
                "permissions": entry.permissions,
                "user": entry.user,
                "group": entry.group,
                "type": entry.type,
                "target": entry.target,
            }
            for entry in lsd_data.entries
        }

        # Compare the dictionaries
        assert pathlib_by_name == lsd_by_name
