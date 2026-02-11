{ pkgs, ... }:
{
  packages = with pkgs; [
    just          # Task runner
    uv            # Python management
    jq            # JSON validation
  ];

  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv.enable = true;
  };

  scripts = {
    fileman.exec = "uv run scripts/fileman \"$@\"";
  };
}
