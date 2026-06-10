# Secrets and CI

## Proxmox API token auth

- Authentication is **API token only**: set `PROXMOX_ENDPOINT`, `PROXMOX_TOKEN_ID`, and `PROXMOX_TOKEN_SECRET` in `~/.config/proxmox-compose/profiles.yml`.

## Secrets

- Use `~/.config/proxmox-compose/profiles.yml` for local profile env vars.
- Use Ansible Vault for repository secrets (`inventory/group_vars/all/vault.yml`).
- If you want non-interactive Ansible Vault, set `ANSIBLE_VAULT_PASSWORD` via `profiles.yml` `secret_env_commands` (for example from `pass`). `proxmox-compose` will automatically pass it to `ansible-playbook` using a temporary `--vault-password-file` script.
- Private Git over HTTPS: store a PAT in vault (for example `github_pat`) and reference it from `vm_compose_apps[].git_token`, or define `deploy_git_app_git_token` only in encrypted `group_vars`/`host_vars` (never in role defaults). Alternatively, export `GITHUB_TOKEN` (or override `deploy_git_app_git_token_env_var`) via `~/.config/proxmox-compose/profiles.yml` (`env` / `secret_env_commands`); `proxmox-compose apply` and `provision-existing` load profile env for `ansible-playbook` before clone. For SSH URLs, prefer `key_file` on the target host.

## Ansible collections

Install required collections once on the Ansible controller (needed for `ansible.posix.authorized_key` in role `common`):

```bash
ansible-galaxy collection install -r config/ansible/collections/requirements.yml
```

## CI validation

### In a workspace created from this scaffold

From the repository root:

```bash
proxmox-compose doctor --workspace .
ansible-galaxy collection install -r config/ansible/collections/requirements.yml
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/provision-infra.yml --syntax-check
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/provision-existing.yml --syntax-check
```

### When maintaining the proxmox-compose CLI repository

The canonical copies of this doc and related templates live under `cli/src/proxmox_compose/scaffold_assets/` in that repo. CI there runs tests and Ansible syntax checks against that embedded tree; see `.github/workflows/validate.yml`.
