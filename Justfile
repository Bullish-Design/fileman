set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

lang := "lsd"

default:
  @just --list

grammar-generate LANG=lang:
  @echo "TODO: generate tree-sitter grammar for {{LANG}}"

grammar-compile LANG=lang:
  @echo "TODO: compile grammar shared library for {{LANG}} into build/"

grammar-test LANG=lang:
  @echo "TODO: run tree-sitter corpus tests for {{LANG}}"

wrapper-generate LANG=lang:
  @echo "TODO: generate wrappers/{{LANG}}-json wrapper script"

test-unit:
  uv run pytest -q

test-correctness:
  uv run pytest tests/test_correctness.py -q

test-all: test-unit test-correctness

lsd-parse PATH=".":
  lsd --long "{{PATH}}" | wrappers/lsd-json --pretty

clean:
  rm -rf .pytest_cache .ruff_cache test_files
  find build -mindepth 1 ! -name '.gitkeep' -delete

rebuild-all: clean grammar-generate grammar-compile wrapper-generate test-all
