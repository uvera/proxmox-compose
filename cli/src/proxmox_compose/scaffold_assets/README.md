# Proxmox Compose

Infrastructure-as-code for Proxmox with Terraform + Ansible, orchestrated by `proxmox-compose`.

## What It Does

- Provisions Proxmox **VMs** (Debian/Fedora) and **LXCs** (Debian only) with Terraform.
- Configures hosts and workloads with Ansible.
- Supports both:
  - greenfield provisioning (`plan` / `apply`)
  - brownfield convergence for existing hosts (`provision-existing`)
- Manages Docker Compose apps on VMs; optional Docker Compose on Debian LXCs; systemd services on Debian LXCs.

## Install CLI (System-Wide)

```bash
pipx install ./cli
```

If already installed and you changed local code:

```bash
pipx install --force ./cli
```

## Core Commands

```bash
proxmox-compose --help
proxmox-compose doctor --workspace .
proxmox-compose plan --workspace .
proxmox-compose apply --workspace .
proxmox-compose provision-existing --workspace .
proxmox-compose inventory sync --workspace .
proxmox-compose logs --workspace . [HOST] [--unit … | --compose-dest … | --container …] [-I|--interactive]  # see proxmox-compose.yml.example
proxmox-compose logs-tui --workspace .
proxmox-compose vault edit --workspace .
```

## Profile SSH Key and Encrypted Proxmox Credentials

You can set an SSH private key in your CLI profile so Ansible uses it for
`plan`, `apply`, `provision-existing`, and remote `logs`, and resolve sensitive values from a
command instead of storing plaintext.

```yaml
profiles:
  default:
    ssh_key_path: ~/.ssh/id_ed25519
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "pass homelab/proxmox_token_secret"
    env:
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
      TF_VAR_proxmox_insecure: "true"
```

`secret_env_commands` supports either a shell-like string command or an argv
list, for example:

```yaml
secret_env_commands:
  TF_VAR_proxmox_token_secret:
    - op
    - read
    - op://Homelab/Proxmox/token_secret
```

### Proxmox API token authentication (token-only)

Authentication is **token-only**. Username/password and TOTP/OTP flows are no
longer supported by the CLI or the Terraform scaffold.

Required `TF_VAR_*` keys for the Terraform provider:

- `TF_VAR_proxmox_endpoint` — for example `https://proxmox.local:8006/api2/json`.
- `TF_VAR_proxmox_token_id` — for example `terraform@pve!proxmox-compose`.
- `TF_VAR_proxmox_token_secret` — the secret paired with that token id.
- `TF_VAR_proxmox_insecure` (optional) — `true` to skip TLS verification on a
  homelab CA.

Create a Proxmox API token (one-time):

1. In the Proxmox UI: **Datacenter → Permissions → API Tokens → Add**.
2. Pick a user (for example `terraform@pve`) and a token id
   (for example `proxmox-compose`); copy the generated secret.
3. Grant the user the privileges your workloads need (for example
   `PVEVMAdmin` on `/`, plus datastore/SDN roles as required).
4. Store the secret outside git — typically via `secret_env_commands` in
   `~/.config/proxmox-compose/profiles.yml`.

Migrating from password / OTP setups:

- Remove any `proxmox_auth_method`, `proxmox_username`, or `proxmox_password`
  values from `terraform.tfvars`, profile env, or shell exports.
- Replace them with the `TF_VAR_proxmox_token_*` variables above.
- Drop any `--prompt-proxmox-otp` flags from your scripts; OTP prompting and
  the `PROXMOX_VE_OTP` plumbing have been removed.

PCI passthrough note:

- API tokens cannot perform some legacy PCI lookups. Prefer **Proxmox resource
  mappings** (Datacenter → Resource Mappings → PCI) and reference mapping ids
  in Terraform; this keeps PCI passthrough compatible with token auth.

## Recommended Workflow

1. Update desired infrastructure in `infra/terraform/environments/homelab`.
2. Run `proxmox-compose doctor --workspace .` to verify binaries/profile/files.
3. Run `proxmox-compose plan --workspace .`.
4. Run `proxmox-compose apply --workspace .`.
5. For pre-existing hosts, define inventory + vars and run:
   `proxmox-compose provision-existing --workspace .`.

## Repository Layout

- `infra/terraform/` - VM/LXC lifecycle and Terraform modules.
- `config/ansible/playbooks/` - orchestration playbooks.
- `config/ansible/roles/` - reusable host/app roles.
- `config/ansible/inventory/` - static + generated inventory.
- `config/ansible/inventory/host_vars/` - per-host overrides (existing host patterns).
- `config/ansible/inventory/group_vars/` - shared variables and vault references.
- `docs/` - onboarding and operational guidance.
- `.cursor/rules/`, `AGENTS.md`, `CLAUDE.md` - AI/agent guidance.

## Existing Host Compose Management

For existing Docker VMs:

1. Add host to `existing_hosts` and/or `existing_docker_vms` in
   `config/ansible/inventory/static.yml`.
2. Create `config/ansible/inventory/host_vars/<host>.yml` (see
   `config/ansible/inventory/host_vars/example_existing_docker_vm.yml`).
3. Choose approach:
   - git-based app (`repo` + `dest`; private **HTTPS** repos: `git_token` from vault, optional vault-backed `deploy_git_app_git_token` in group_vars, or `GITHUB_TOKEN` from profile env — see `docs/secrets-and-ci.md`)
   - SSH Git URLs: `repo: git@github.com:org/repo.git` with `key_file` (deploy key on the target host)
   - inline compose (`compose_file_content`)
   - optional `.env` injection (`env_content`) from vault-backed variables
4. Run `provision-existing`.
   - `proxmox-compose` relies on inventory-native var discovery in
     `config/ansible/inventory/host_vars/` and `config/ansible/inventory/group_vars/`.

To update Frigate image tag as code:
- edit image in host vars compose definition
- re-run `provision-existing`

## Secrets

- Keep secret values out of tracked files.
- Put sensitive vars into encrypted vault files (for example
  `config/ansible/inventory/group_vars/all/vault.yml`).
- Reference those values from host/group vars (for example `.env` content,
  or `git_token: "{{ github_pat }}"` for private HTTPS checkouts).
- Operator-only Git tokens can live in `profiles.yml` so they never reach git:

```yaml
profiles:
  default:
    secret_env_commands:
      GITHUB_TOKEN: "pass github/my_token"
```

## Validation

Before pushing changes:

```bash
proxmox-compose doctor --workspace .
terraform fmt -check -recursive infra/terraform
cd infra/terraform/environments/homelab && terraform init -backend=false && terraform validate
cd ../../../..
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
```
