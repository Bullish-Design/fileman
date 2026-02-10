set shell := ["zsh", "-eu", "-o", "pipefail", "-c"]

os_name := os()
shared_flag := if os_name == "macos" { "-dynamiclib" } else { "-shared" }
lib_ext := if os_name == "macos" { "dylib" } else { "so" }

# Generate parser sources for a tree-sitter grammar.
grammar-generate lang:
    @echo "Generating tree-sitter grammar for {{lang}}"
    cd grammars/tree-sitter-{{lang}} && tree-sitter generate

# Compile parser source into a platform-specific shared library.
grammar-compile lang:
    @echo "Compiling tree-sitter grammar for {{lang}} -> build/{{lang}}.{{lib_ext}}"
    mkdir -p build
    cc {{shared_flag}} -fPIC \
      -Igrammars/tree-sitter-{{lang}}/src \
      grammars/tree-sitter-{{lang}}/src/parser.c \
      -o build/{{lang}}.{{lib_ext}}


lang := "lsd"

default:
  @just --list

#grammar-generate LANG=lang:
#  @echo "TODO: generate tree-sitter grammar for {{LANG}}"

#grammar-compile LANG=lang:
#  @echo "TODO: compile grammar shared library for {{LANG}} into build/"

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

#rebuild-all: clean grammar-generate grammar-compile wrapper-generate test-all
