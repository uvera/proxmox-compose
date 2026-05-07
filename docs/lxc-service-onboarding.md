# Debian LXC Service Onboarding

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Optional: set `go_install_path` on a `lxc_git_apps` entry to compile a Go module after `git` checkout.
   Optional: set `go_version` (for example `1.25.0`) when building **on the LXC** (`lxc_go_build_local: false`) to bootstrap that toolchain from go.dev.
   By default `lxc_go_build_local` is true in the scaffold: Go binaries build on the Ansible controller (install `go` there). Set `lxc_go_build_local: false` to compile on the guest instead.
4. Optional (Python apps): define `lxc_python_apps` entries to create a venv, install editable dependencies, and run migrations.
5. Define `lxc_systemd_services` entries with `exec_start`; optional `environment_file` / `environment_files` for systemd `EnvironmentFile=`.
6. Re-run `proxmox-compose apply`.
