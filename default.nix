{pkgs ? (import <nixpkgs> {}), ...} :
let
  python = import ./requirements.nix { inherit pkgs; };
in python.mkDerivation rec {
  name = "youstat";
  version = "0.1.0";
  buildInputs = [ pkgs.zip pkgs.pypi2nix ];
  propagatedBuildInputs = builtins.attrValues python.packages;
  src = ./.;
}
