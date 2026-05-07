# Secrets and CI

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
