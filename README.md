# Proxmox Compose

This **git repository is the `proxmox-compose` CLI** and its embedded Terraform/Ansible **scaffold** for user projects. It is not a homelab deployment: after `proxmox-compose init`, you work in your own repository that contains `infra/terraform/` and `config/ansible/`.

`proxmox-compose` orchestrates Proxmox infrastructure-as-code for those workspaces.

## What It Does

- Provisions Proxmox **VMs** (Debian/Fedora) and **LXCs** (Debian only) with Terraform.
- Configures hosts and workloads with Ansible.
- Supports both:
  - greenfield provisioning (`plan` / `apply`)
  - brownfield convergence for existing hosts (`provision-existing`)
- Manages Docker Compose apps on VMs and systemd services on Debian LXCs.

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
proxmox-compose vault edit --workspace .
```

## Profile SSH Key and Encrypted Proxmox Credentials

You can set an SSH private key in your CLI profile so Ansible uses it for
`plan`, `apply`, and `provision-existing`, and resolve sensitive values from a
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

## Recommended Workflow (in your scaffolded repository)

1. Initialize a git repository and run `proxmox-compose init --path .` (see `proxmox-compose init --help`).
2. Update desired infrastructure in `infra/terraform/environments/homelab`.
3. Run `proxmox-compose doctor --workspace .` to verify binaries/profile/files.
4. Run `proxmox-compose plan --workspace .`.
5. Run `proxmox-compose apply --workspace .`.
6. For pre-existing hosts, define inventory + vars and run:
   `proxmox-compose provision-existing --workspace .`.

## This repository (CLI source)

- `cli/` - Python package (`pipx install ./cli`).
- `cli/src/proxmox_compose/scaffold_assets/` - templates copied by `init` / `scaffold sync`: Terraform, Ansible, docs, sample workflow files.
- `docs/` - contributor-facing notes; user-facing guides are also embedded under `scaffold_assets/docs/`.
- `.cursor/rules/`, `AGENTS.md`, `CLAUDE.md` - AI/agent guidance for working on this repo.

Scaffolded **user** repositories include paths such as `infra/terraform/`, `config/ansible/playbooks/`, roles, inventory, etc.—see the generated layout after `init`.

## Scaffolded repository layout (after `init`)

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
   - git-based app (`repo` + `dest`)
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
- Reference those values from host/group vars (for example `.env` content).

## Validation

**Contributors (this CLI repo):**

```bash
PYTHONPATH=cli/src python -m pytest cli/tests -q
terraform fmt -check -recursive cli/src/proxmox_compose/scaffold_assets/infra/terraform
( cd cli/src/proxmox_compose/scaffold_assets/infra/terraform/environments/homelab && terraform init -backend=false && terraform validate )
( cd cli/src/proxmox_compose/scaffold_assets/config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check )
```

**Your provisioned workspace (after `init`):**

```bash
proxmox-compose doctor --workspace .
terraform fmt -check -recursive infra/terraform
cd infra/terraform/environments/homelab && terraform init -backend=false && terraform validate
cd ../../../..
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
```
