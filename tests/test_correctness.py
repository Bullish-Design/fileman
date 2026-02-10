from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_wrapper_smoke_emits_json() -> None:
    """Smoke test placeholder for wrapper availability + JSON output."""
    wrapper = Path(os.environ.get("FILEMAN_WRAPPER", "wrappers/lsd-json"))

    assert wrapper.exists(), f"wrapper not found: {wrapper}"
    assert wrapper.is_file(), f"wrapper is not a file: {wrapper}"
    assert os.access(wrapper, os.X_OK), f"wrapper is not executable: {wrapper}"

    sample_input = "-rw-r--r-- user group 1 B Fri Jan 15 10:29:33 2025 hello.txt\n"

    proc = subprocess.run(
        [str(wrapper)],
        input=sample_input,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert isinstance(payload, dict)
    assert "lines" in payload
    assert isinstance(payload["lines"], list)
