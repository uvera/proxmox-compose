# Debian LXC Service Onboarding

For **Docker Compose on an LXC** (instead of systemd apps), see [lxc-docker-compose.md](lxc-docker-compose.md).

To run **Tailscale Serve or Funnel on the same Debian LXC** (native `tailscaled` alongside Compose or systemd workloads), see [tailscale-on-lxc.md](tailscale-on-lxc.md).

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Optional: set `go_install_path` on a `lxc_git_apps` entry to compile a Go module after `git` checkout.
   Optional: set `go_version` (for example `1.25.0`) when building **on the LXC** (`lxc_go_build_local: false`) to bootstrap that toolchain from go.dev.
   By default `lxc_go_build_local` is true (see `group_vars/all/main.yml`): Go binaries build on the Ansible controller and are copied to the LXC (install `go` on the machine running Ansible). Set `lxc_go_build_local: false` to compile on the guest instead.
4. Optional (Python apps): define `lxc_python_apps` entries to create a venv, install editable dependencies, and run migrations.
   Optional: set `extras: ["daemon", "..."]` on a `lxc_python_apps` entry to install PEP 508 extras (renders as `pip install -e "<app_dir>[extra1,extra2]"`).
5. Optional: define `lxc_runtime_dirs` entries (`path`, `owner`, `group`, `mode`) for state / cache / output directories the service user must own (created before the unit starts; use for paths referenced in `EnvironmentFile=`).
6. Define `lxc_systemd_services` entries with `exec_start`; optional `environment_file` / `environment_files` for systemd `EnvironmentFile=`.
7. Re-run `proxmox-compose apply`.
