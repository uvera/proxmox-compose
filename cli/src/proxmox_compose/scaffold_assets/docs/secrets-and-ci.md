# Secrets and CI

## Secrets
- Keep `terraform.tfvars` local (ignored) for secrets and machine-specific overrides.
- Keep shared non-secret Terraform values in tracked `*.auto.tfvars` files (for example `homelab.shared.auto.tfvars`).
- For Debian LXC SSH key defaults, set `default_lxc_ssh_public_key_path` in local `terraform.tfvars`; keep `file(...)`/`pathexpand(...)` calls in `.tf` files, not in tfvars values.
- Prefer profile `env`/`secret_env_commands` (`TF_VAR_*`) for provider auth values; avoid redefining them in tfvars files because tfvars takes precedence over environment variables.
- Use `~/.config/proxmox-compose/profiles.yml` for local profile env vars.
- Use Ansible Vault for repository secrets (`inventory/group_vars/all/vault.yml`).

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
