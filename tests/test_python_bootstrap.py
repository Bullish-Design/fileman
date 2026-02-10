from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WRAPPER_PATH = REPO_ROOT / "wrappers" / "python-json"


def _compile_with_local_tools(ext: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "cc",
            "-shared" if platform.system() != "Darwin" else "-dynamiclib",
            "-fPIC",
            "-Igrammars/tree-sitter-python/src",
            "grammars/tree-sitter-python/src/parser.c",
            "-o",
            f"build/python.{ext}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_python_grammar_library() -> None:
    ext = "dylib" if platform.system() == "Darwin" else "so"
    grammar_lib = REPO_ROOT / "build" / f"python.{ext}"
    parser_source = REPO_ROOT / "grammars" / "tree-sitter-python" / "src" / "parser.c"

    if grammar_lib.exists():
        return

    if not parser_source.exists():
        if shutil.which("just"):
            gen = subprocess.run(
                ["just", "grammar-generate", "python"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if gen.returncode != 0:
                pytest.skip(f"could not generate parser.c: {gen.stderr or gen.stdout}")
        elif shutil.which("tree-sitter"):
            gen = subprocess.run(
                ["tree-sitter", "generate"],
                cwd=REPO_ROOT / "grammars" / "tree-sitter-python",
                capture_output=True,
                text=True,
            )
            if gen.returncode != 0:
                pytest.skip(f"could not generate parser.c: {gen.stderr or gen.stdout}")
        else:
            pytest.skip("parser.c missing and neither `just` nor `tree-sitter` is available")

    grammar_lib.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("just"):
        comp = subprocess.run(
            ["just", "grammar-compile", "python"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
    elif shutil.which("cc"):
        comp = _compile_with_local_tools(ext)
    else:
        pytest.skip("cannot compile grammar library: neither `just` nor `cc` is available")

    if comp.returncode != 0:
        pytest.skip(f"could not compile python grammar library: {comp.stderr or comp.stdout}")


def run_wrapper(*args: str, input_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(WRAPPER_PATH), *args],
        cwd=REPO_ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_wrapper_parses_python_function_and_emits_expected_nodes() -> None:
    proc = run_wrapper(input_text="def f(x): return x + 1\n")
    assert proc.returncode == 0, proc.stderr

    payload = json.loads(proc.stdout)
    assert payload["type"] in {"module", "source_file"}

    child_types = {child["type"] for child in payload["children"]}
    assert "function_definition" in child_types


def test_wrapper_pretty_output_is_multiline_json() -> None:
    proc = run_wrapper("--pretty", input_text="def f(x): return x + 1\n")
    assert proc.returncode == 0, proc.stderr
    assert "\n" in proc.stdout

    payload = json.loads(proc.stdout)
    assert payload["type"] in {"module", "source_file"}


def test_wrapper_include_text_and_max_text_truncates_output() -> None:
    source = "def f(x): return x + 123456\n"

    include_text_proc = run_wrapper("--include-text", input_text=source)
    assert include_text_proc.returncode == 0, include_text_proc.stderr
    payload = json.loads(include_text_proc.stdout)
    assert "text" in payload
    assert payload["text"].startswith("def f(x)")

    max_text_proc = run_wrapper("--include-text", "--max-text", "5", input_text=source)
    assert max_text_proc.returncode == 0, max_text_proc.stderr
    truncated_payload = json.loads(max_text_proc.stdout)
    assert truncated_payload["text"] == "def f..."


def _load_wrapper_module():
    spec = importlib.util.spec_from_file_location("python_json_wrapper", WRAPPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wrapper_non_zero_exit_for_missing_grammar_library() -> None:
    ext = "dylib" if platform.system() == "Darwin" else "so"
    grammar_lib = REPO_ROOT / "build" / f"python.{ext}"
    backup_lib = grammar_lib.with_suffix(grammar_lib.suffix + ".bak")

    if grammar_lib.exists():
        shutil.move(grammar_lib, backup_lib)

    try:
        proc = run_wrapper(input_text="def f(x): return x + 1\n")
        assert proc.returncode != 0
        assert "grammar shared library not found" in proc.stderr
    finally:
        if backup_lib.exists():
            shutil.move(backup_lib, grammar_lib)


def test_load_language_raises_for_invalid_library_path() -> None:
    wrapper_module = _load_wrapper_module()

    with pytest.raises(FileNotFoundError):
        wrapper_module.load_language(REPO_ROOT / "build" / "does-not-exist.so")
