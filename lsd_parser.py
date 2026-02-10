#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
# ]
# ///

"""Parse lsd --long output and convert to Pydantic models."""

import sys
import json
import re
import subprocess
from pathlib import Path
from models import FileEntry, FileListings


def parse_lsd_line(line: str) -> FileEntry | None:
    """Parse a single line of lsd --long output.

    Example formats:
    drwxr-xr-x user group 4.0 KB Fri Jan 15 10:30:45 2025 dirname
    -rw-r--r-- user group 1.2 MB Fri Jan 15 10:29:33 2025 filename.txt
    lrwxrwxrwx user group   15 B Fri Jan 15 10:31:02 2025 link -> target
    """
    line = line.strip()
    if not line:
        return None

    # Split the line into components
    # Pattern: permissions user group size timestamp... name [-> target]
    # The timestamp format includes day name, month, day, time, year (5 components)

    parts = line.split()
    if len(parts) < 9:  # Minimum: perms user group size_val size_unit day month daynum time year name
        return None

    # Extract fixed-position fields
    permissions = parts[0]
    user = parts[1]
    group = parts[2]

    # Size can be "4.0 KB" or "15 B" (value + unit)
    size_value = parts[3]
    size_unit = parts[4]
    size = f"{size_value} {size_unit}"

    # Timestamp: "Fri Jan 15 10:30:45 2025" (5 parts)
    timestamp_parts = parts[5:10]
    timestamp = " ".join(timestamp_parts)

    # Everything after timestamp is the name (and possibly " -> target")
    name_parts = parts[10:]
    name_str = " ".join(name_parts)

    # Check for symlink target
    target = None
    if " -> " in name_str:
        name, target = name_str.split(" -> ", 1)
    else:
        name = name_str

    # Determine type from permissions
    if permissions.startswith("d"):
        file_type = "directory"
    elif permissions.startswith("l"):
        file_type = "symlink"
    else:
        file_type = "file"

    # Build entry data
    entry_data = {
        "permissions": permissions,
        "user": user,
        "group": group,
        "size": size,
        "timestamp": timestamp,
        "name": name,
        "type": file_type,
    }

    if target is not None:
        entry_data["target"] = target

    return FileEntry(**entry_data)


def parse_lsd_output(output: str) -> FileListings:
    """Parse complete lsd --long output into FileListings."""
    entries = []

    for line in output.splitlines():
        entry = parse_lsd_line(line)
        if entry is not None:
            entries.append(entry)

    return FileListings(entries=entries)


def run_lsd(path: Path) -> str:
    """Execute lsd --long on the given path and return output."""
    try:
        result = subprocess.run(
            ["lsd", "--long", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running lsd: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'lsd' command not found. Please install lsd.", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path(".")

    if not target_path.exists():
        print(f"Error: Path '{target_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Run lsd and get output
    lsd_output = run_lsd(target_path)

    # Parse output
    listings = parse_lsd_output(lsd_output)

    # Output JSON
    print(listings.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
