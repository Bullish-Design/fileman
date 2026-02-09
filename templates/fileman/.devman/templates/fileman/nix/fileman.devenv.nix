{ pkgs, ... }:
let
  py = pkgs.python3.withPackages (ps: [ ps.pydantic ]);

  fileman = pkgs.writeShellApplication {
    name = "fileman";
    runtimeInputs = [ py pkgs.lsd ];
    text = ''
      # Expect to run inside a repo that has .devman -> instance symlink.
      exec python3 ./.devman/fileman/src/fileman_snapshot.py "$@"
    '';
  };
in
{
  packages = [
    pkgs.lsd
    py
    fileman
  ];
}
