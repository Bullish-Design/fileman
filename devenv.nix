{ pkgs, ... }:
{
  packages = with pkgs; [
    just
    tree-sitter
    gcc
    python312
    uv
    lsd
  ];

  scripts.fileman-help.exec = ''
    echo "Fileman development shell"
    echo "- just test-correctness"
    echo "- just lsd-parse <path>"
  '';
}
