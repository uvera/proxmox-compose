# Proxmox Compose

Infrastructure-as-code for Proxmox with Terraform + Ansible, orchestrated by `proxmox-compose`.

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
```

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
- `config/ansible/host_vars/` - per-host overrides (existing host patterns).
- `config/ansible/group_vars/` - shared variables and vault references.
- `docs/` - onboarding and operational guidance.
- `.cursor/rules/`, `AGENTS.md`, `CLAUDE.md` - AI/agent guidance.

## Existing Host Compose Management

For existing Docker VMs:

1. Add host to `existing_hosts` and/or `existing_docker_vms` in
   `config/ansible/inventory/static.yml`.
2. Create `config/ansible/host_vars/<host>.yml` (see
   `config/ansible/host_vars/example_existing_docker_vm.yml`).
3. Choose approach:
   - git-based app (`repo` + `dest`)
   - inline compose (`compose_file_content`)
   - optional `.env` injection (`env_content`) from vault-backed variables
4. Run `provision-existing`.

To update Frigate image tag as code:
- edit image in host vars compose definition
- re-run `provision-existing`

## Secrets

- Keep secret values out of tracked files.
- Put sensitive vars into encrypted vault files (for example
  `config/ansible/group_vars/all/vault.yml`).
- Reference those values from host/group vars (for example `.env` content).

## Validation

Before pushing changes:

```bash
proxmox-compose doctor --workspace .
terraform fmt -check -recursive infra/terraform
cd infra/terraform/environments/homelab && terraform init -backend=false && terraform validate
cd ../../../..
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
```
