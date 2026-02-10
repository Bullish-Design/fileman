#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
# ]
# ///

"""Collect file system data using pathlib and populate Pydantic models."""

import sys
import json
import stat
import pwd
import grp
from pathlib import Path
from datetime import datetime
from models import FileEntry, FileListings


def format_permissions(mode: int) -> str:
    """Convert numeric file mode to lsd-style permission string."""
    # File type character
    if stat.S_ISDIR(mode):
        type_char = "d"
    elif stat.S_ISLNK(mode):
        type_char = "l"
    else:
        type_char = "-"

    # Owner permissions
    owner = ""
    owner += "r" if mode & stat.S_IRUSR else "-"
    owner += "w" if mode & stat.S_IWUSR else "-"
    owner += "x" if mode & stat.S_IXUSR else "-"

    # Group permissions
    group = ""
    group += "r" if mode & stat.S_IRGRP else "-"
    group += "w" if mode & stat.S_IWGRP else "-"
    group += "x" if mode & stat.S_IXGRP else "-"

    # Other permissions
    other = ""
    other += "r" if mode & stat.S_IROTH else "-"
    other += "w" if mode & stat.S_IWOTH else "-"
    other += "x" if mode & stat.S_IXOTH else "-"

    return f"{type_char}{owner}{group}{other}"


def format_size(size_bytes: int) -> str:
    """Convert size in bytes to human-readable format matching lsd output."""
    units = [("B", 1), ("KB", 1024), ("MB", 1024**2), ("GB", 1024**3), ("TB", 1024**4)]

    for unit_name, unit_size in reversed(units):
        if size_bytes >= unit_size:
            value = size_bytes / unit_size
            if value >= 10:
                return f"{value:.0f} {unit_name}"
            else:
                return f"{value:.1f} {unit_name}"

    return f"{size_bytes} B"


def format_timestamp(timestamp: float) -> str:
    """Convert Unix timestamp to lsd-style timestamp string."""
    dt = datetime.fromtimestamp(timestamp)
    # Format: "Fri Jan 15 10:30:45 2025"
    return dt.strftime("%a %b %d %H:%M:%S %Y")


def get_file_type(path: Path) -> str:
    """Determine file type (file, directory, or symlink)."""
    if path.is_symlink():
        return "symlink"
    elif path.is_dir():
        return "directory"
    else:
        return "file"


def collect_entry(path: Path) -> FileEntry:
    """Collect information about a single file system entry."""
    # Get stat info (follow_symlinks=False to get symlink info, not target)
    st = path.lstat()

    # Get owner and group names
    try:
        user = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        user = str(st.st_uid)

    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)

    # Build entry data
    entry_data = {
        "permissions": format_permissions(st.st_mode),
        "user": user,
        "group": group,
        "size": format_size(st.st_size),
        "timestamp": format_timestamp(st.st_mtime),
        "name": path.name,
        "type": get_file_type(path),
    }

    # Add target for symlinks
    if path.is_symlink():
        try:
            entry_data["target"] = str(path.readlink())
        except (OSError, RuntimeError):
            entry_data["target"] = "???"

    return FileEntry(**entry_data)


def collect_directory(directory: Path) -> FileListings:
    """Collect all entries in a directory."""
    entries = []

    try:
        for item in sorted(directory.iterdir(), key=lambda p: p.name):
            try:
                entry = collect_entry(item)
                entries.append(entry)
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not access {item}: {e}", file=sys.stderr)
    except PermissionError as e:
        print(f"Error: Cannot read directory {directory}: {e}", file=sys.stderr)
        sys.exit(1)

    return FileListings(entries=entries)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path(".")

    if not target_path.exists():
        print(f"Error: Path '{target_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not target_path.is_dir():
        print(f"Error: Path '{target_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Collect data
    listings = collect_directory(target_path)

    # Output JSON
    print(listings.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
