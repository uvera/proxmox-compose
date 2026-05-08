# Secrets and CI

## Secrets
- Scaffold templates ship from `cli/src/proxmox_compose/scaffold_assets/`. In a **generated** workspace (after `proxmox-compose init`), keep `terraform.tfvars` local (ignored) for secrets and machine-specific overrides.
- Keep shared non-secret Terraform values in tracked `*.auto.tfvars` files (for example `homelab.shared.auto.tfvars`) in that workspace.
- For Debian LXC SSH key defaults, set `default_lxc_ssh_public_key_path` in local `terraform.tfvars`; keep `file(...)`/`pathexpand(...)` calls in `.tf` files, not in tfvars values.
- Prefer profile `env`/`secret_env_commands` (`TF_VAR_*`) for provider auth values; avoid redefining them in tfvars files because tfvars takes precedence over environment variables.
- Use `~/.config/proxmox-compose/profiles.yml` for local profile env vars.
- Use Ansible Vault for repository secrets in workspaces (`inventory/group_vars/all/vault.yml`).
- If you want non-interactive Ansible Vault, set `ANSIBLE_VAULT_PASSWORD` via `profiles.yml` `secret_env_commands` (for example from `pass`). The CLI will automatically pass it to `ansible-playbook` using a temporary `--vault-password-file` script.
- Private Git over HTTPS in the scaffold: store a PAT in vault (for example `github_pat`) and reference `vm_compose_apps[].git_token`, or define `deploy_git_app_git_token` only in vault-backed inventory (not role defaults), or export `GITHUB_TOKEN` via `profiles.yml` before `apply` / `provision-existing`. For SSH URLs, use `key_file` on the host.

## CI Validation (this CLI repository)
Run these checks in CI (see `.github/workflows/validate.yml`):
1. `terraform fmt -check -recursive cli/src/proxmox_compose/scaffold_assets/infra/terraform`
2. `terraform validate` from `cli/src/proxmox_compose/scaffold_assets/infra/terraform/environments/homelab`
3. `ansible-playbook --syntax-check` from `cli/src/proxmox_compose/scaffold_assets/config/ansible`

In a **user workspace** created from the scaffold, use the same commands with `infra/terraform` and `config/ansible` at the repository root.
