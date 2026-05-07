# Debian LXC Service Onboarding

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Optional: set `go_install_path` on a `lxc_git_apps` entry to compile a Go module after `git` checkout.
   Optional: set `go_version` (for example `1.25.0`) to bootstrap that Go toolchain from go.dev before build.
   Optional: set `go_build_args` (list) and `go_build_environment` (map) to tune Go builds for constrained LXCs.
4. Define `lxc_systemd_services` entries with `exec_start`; optional `environment_file` / `environment_files` for systemd `EnvironmentFile=`.
5. Re-run `proxmox-compose apply`.
