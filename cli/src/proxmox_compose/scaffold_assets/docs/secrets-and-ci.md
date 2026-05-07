# Secrets and CI

## Secrets
- Keep `terraform.tfvars` local (ignored) for secrets and machine-specific overrides.
- Keep shared non-secret Terraform values in tracked `*.auto.tfvars` files (for example `homelab.shared.auto.tfvars`).
- For Debian LXC SSH key defaults, set `default_lxc_ssh_public_key_path` in local `terraform.tfvars`; keep `file(...)`/`pathexpand(...)` calls in `.tf` files, not in tfvars values.
- Prefer profile `env`/`secret_env_commands` (`TF_VAR_*`) for provider auth values; avoid redefining them in tfvars files because tfvars takes precedence over environment variables.
- Use `~/.config/proxmox-compose/profiles.yml` for local profile env vars.
- Use Ansible Vault for repository secrets (`inventory/group_vars/all/vault.yml`).
- Private Git over HTTPS: store a PAT in vault (for example `github_pat`) and reference it from `vm_compose_apps[].git_token`, or define `deploy_git_app_git_token` only in encrypted `group_vars`/`host_vars` (never in role defaults). Alternatively, export `GITHUB_TOKEN` (or override `deploy_git_app_git_token_env_var`) via `~/.config/proxmox-compose/profiles.yml` (`env` / `secret_env_commands`); `proxmox-compose apply` and `provision-existing` load profile env for `ansible-playbook` before clone. For SSH URLs, prefer `key_file` on the target host.

## CI Validation
Run these checks in CI:
1. `terraform fmt -check`
2. `terraform validate`
3. `ansible-playbook --syntax-check`

Example from the repository root of this workspace:

```bash
terraform fmt -check -recursive infra/terraform
cd infra/terraform/environments/homelab && terraform init -backend=false && terraform validate
cd ../../../..
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
```
