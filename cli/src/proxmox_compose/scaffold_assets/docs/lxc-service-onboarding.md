# Debian LXC Service Onboarding

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Optional: set `go_install_path` on a `lxc_git_apps` entry to compile a Go module after `git` checkout.
   Optional: set `go_version` (for example `1.25.0`) to bootstrap that Go toolchain from go.dev before build.
   Optional: set `lxc_go_build_local: true` to build the Go binary on the Ansible controller and copy it to the LXC.
4. Optional (Python apps): define `lxc_python_apps` entries to create a venv, install editable dependencies, and run migrations.
   Optional: set `extras: ["daemon", "..."]` on a `lxc_python_apps` entry to install PEP 508 extras (renders as `pip install -e "<app_dir>[extra1,extra2]"`).
5. Optional: define `lxc_runtime_dirs` entries (`path`, `owner`, `group`, `mode`) for state / cache / output directories the service user must own (created before the unit starts; use for paths referenced in `EnvironmentFile=`).
6. Define `lxc_systemd_services` entries with `exec_start`; optional `environment_file` / `environment_files` for systemd `EnvironmentFile=`.
7. Re-run `proxmox-compose apply`.
