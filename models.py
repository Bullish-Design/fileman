"""Pydantic models for file listing data structures."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class FileEntry(BaseModel):
    """Represents a single file system entry from lsd output."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "permissions": "drwxr-xr-x",
                    "user": "user",
                    "group": "group",
                    "size": "4.0 KB",
                    "timestamp": "Fri Jan 15 10:30:45 2025",
                    "name": "directory_name",
                    "type": "directory"
                },
                {
                    "permissions": "-rw-r--r--",
                    "user": "user",
                    "group": "group",
                    "size": "1.2 MB",
                    "timestamp": "Fri Jan 15 10:29:33 2025",
                    "name": "file.txt",
                    "type": "file"
                },
                {
                    "permissions": "lrwxrwxrwx",
                    "user": "user",
                    "group": "group",
                    "size": "15 B",
                    "timestamp": "Fri Jan 15 10:31:02 2025",
                    "name": "link",
                    "target": "/path/to/target",
                    "type": "symlink"
                }
            ]
        }
    )

    permissions: str = Field(..., description="Unix permission string (e.g., 'drwxr-xr-x')")
    user: str = Field(..., description="Owner username")
    group: str = Field(..., description="Owner group")
    size: str = Field(..., description="Human-readable size (e.g., '4.0 KB')")
    timestamp: str = Field(..., description="Last modified timestamp")
    name: str = Field(..., description="File or directory name")
    type: Literal["file", "directory", "symlink"] = Field(..., description="Entry type")
    target: Optional[str] = Field(None, description="Symlink target (symlinks only)")


class FileListings(BaseModel):
    """Container for multiple file system entries."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "entries": [
                        {
                            "permissions": "drwxr-xr-x",
                            "user": "user",
                            "group": "group",
                            "size": "4.0 KB",
                            "timestamp": "Fri Jan 15 10:30:45 2025",
                            "name": "docs",
                            "type": "directory"
                        },
                        {
                            "permissions": "-rw-r--r--",
                            "user": "user",
                            "group": "group",
                            "size": "256 B",
                            "timestamp": "Fri Jan 15 10:29:33 2025",
                            "name": "README.md",
                            "type": "file"
                        }
                    ]
                }
            ]
        }
    )

    entries: list[FileEntry] = Field(default_factory=list, description="List of file entries")
