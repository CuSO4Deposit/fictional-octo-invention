{
  description = "Description for the project";

  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pre-commit-hooks.url = "github:cachix/git-hooks.nix";
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.pre-commit-hooks.flakeModule
      ];
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      perSystem =
        {
          config,
          self',
          inputs',
          pkgs,
          system,
          ...
        }:
        {
          pre-commit.settings = {
            src = ./.;
            hooks = {
              nixfmt.enable = true;
              ruff.enable = true;
              ruff-format.enable = true;
            };
          };
          devShells = {
            default = pkgs.mkShellNoCC {
              buildInputs = with pkgs; [
                python313
                uv
              ];
              shellHook = ''
                # install pre-commit hooks
                ${config.pre-commit.installationScript}

                # Only the C++ runtime and zlib belong here: numpy's manylinux wheels
                # need them, but a glibc in LD_LIBRARY_PATH shadows the glibc of every
                # Nix binary in the shell, because the loader checks LD_LIBRARY_PATH
                # before RUNPATH. That breaks git/nix/coreutils with "GLIBC_2.4x not
                # found" or stack smashing as soon as the system nixpkgs is newer than
                # this flake's lock.
                export LD_LIBRARY_PATH="${
                  pkgs.lib.makeLibraryPath [
                    pkgs.stdenv.cc.cc.lib
                    pkgs.zlib
                  ]
                }:$LD_LIBRARY_PATH";

                # Explicit --python so an existing venv built by another interpreter
                # is switched, not silently kept.
                uv venv --allow-existing --python ${pkgs.python313}/bin/python
                . .venv/bin/activate
                uv sync
              '';
            };
          };
        };
    };
}
