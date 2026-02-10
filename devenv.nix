{ pkgs, ... }:
{
  env.TREESITTER_PARSER_PATH = "/home/andrew/Documents/Projects/grammatic/build/python/python.so";
  env.LOCAL_PARSER_PATH = "./.devman/.grammatic/python.so";

  packages = with pkgs; [
    just
    tree-sitter
    gcc
    python312
    uv
    lsd
  ];

  scripts.fileman-help.exec = ''
    echo
    echo
    echo "Fileman development shell"
    echo "- just test-correctness"
    echo "- just lsd-parse <path>"
  '';

  scripts.link-treesitter-parser.exec = ''
    parser_path="$1"
    target_path="$2"

    if [ -z "$parser_path" ]; then
      echo "❌ TREESITTER_PARSER_PATH is not set; skipping parser symlink."
      exit 1
    fi

    if [ ! -f "$parser_path" ]; then
      echo "❌ Parser file not found at: $parser_path"
      exit 1
    fi

    mkdir -p "$(dirname "$target_path")"

    if ln -sf "$parser_path" "$target_path"; then
      echo "✅ Linked parser: $parser_path -> $target_path"
    else
      echo "❌ Failed to link parser: $parser_path -> $target_path"
      exit 1
    fi
  '';

  enterShell = ''
    fileman-help
    echo
    echo
    link-treesitter-parser "$TREESITTER_PARSER_PATH" "$LOCAL_PARSER_PATH" || true
    echo
    echo
  '';
}
