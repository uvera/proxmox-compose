# Homelab Terraform environment

Token-only Proxmox provider configuration: set `proxmox_endpoint`, `proxmox_token_id`, and `proxmox_token_secret` (typically via `TF_VAR_*` in `~/.config/proxmox-compose/profiles.yml`, or in git-ignored `terraform.tfvars`). Copy `terraform.tfvars.example` as a starting point.

## Migrating from password or OTP-based auth

Older scaffolds supported `proxmox_auth_method = "password"` with username/password and optional `PROXMOX_VE_OTP` / `--prompt-proxmox-otp`. That path has been removed.

1. **Create a Proxmox API token** for a dedicated automation user (Datacenter → Permissions → API Tokens). Grant only the privileges your Terraform modules need.
2. **Remove** `proxmox_auth_method`, `proxmox_username`, `proxmox_password`, and any OTP-related exports or CLI flags from scripts and CI.
3. **Set** `TF_VAR_proxmox_token_id`, `TF_VAR_proxmox_token_secret`, and `TF_VAR_proxmox_endpoint` (see root `README.md`, Profile SSH Key and Encrypted Proxmox Credentials).
4. Run `terraform validate` from this directory after refreshing `.tf` files from `proxmox-compose scaffold sync`.

See also `docs/secrets-and-ci.md` in the scaffold for Ansible/Git secrets.
