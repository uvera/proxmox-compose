# Debian LXC Service Onboarding

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Define `lxc_systemd_services` entries with `exec_start`.
4. Re-run `proxmox-compose apply`.
