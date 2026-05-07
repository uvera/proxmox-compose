DOCS_SCAFFOLD_FILES: dict[str, str] = {
    "docs/service-onboarding.md": """# VM Service Onboarding

Use this flow for VM docker-compose apps (for example Frigate):
1. Add VM definition in Terraform vars.
2. Add host to `debian_vms` or `fedora_vms` inventory grouping.
3. Set `vm_compose_apps` host/group vars with repo and destination.
4. Re-run `proxmox-compose apply`.
""",
    "docs/lxc-service-onboarding.md": """# Debian LXC Service Onboarding

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Optional: set `go_install_path` on a `lxc_git_apps` entry to compile a Go module after `git` checkout.
   Optional: set `go_version` (for example `1.25.0`) to bootstrap that Go toolchain from go.dev before build.
   Optional: set `lxc_go_build_local: true` to build the Go binary on the Ansible controller and copy it to the LXC.
4. Optional (Python apps): define `lxc_python_apps` entries to create a venv, install editable dependencies, and run migrations.
5. Define `lxc_systemd_services` entries with `exec_start`; optional `environment_file` / `environment_files` for systemd `EnvironmentFile=`.
6. Re-run `proxmox-compose apply`.
""",
    "docs/secrets-and-ci.md": """# Secrets and CI

## Secrets
- Keep `terraform.tfvars` local (ignored) for secrets and machine-specific overrides.
- Keep shared non-secret Terraform values in tracked `*.auto.tfvars` files (for example `homelab.shared.auto.tfvars`).
- Prefer profile `env`/`secret_env_commands` (`TF_VAR_*`) for provider auth values; avoid redefining them in tfvars files because tfvars takes precedence over environment variables.
- Use `~/.config/proxmox-compose/profiles.yml` for local profile env vars.
- Use Ansible Vault for repository secrets (`inventory/group_vars/all/vault.yml`).

## CI Validation
Run these checks in CI:
1. `terraform fmt -check`
2. `terraform validate`
3. `ansible-playbook --syntax-check`
""",
}

