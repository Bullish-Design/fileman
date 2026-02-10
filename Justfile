set shell := ["bash", "-cu"]

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
