# Proxmox Compose

This repository contains the `proxmox-compose` CLI and scaffold templates used by `proxmox-compose init`.

The default model is now **Ansible-first**:
- inventory and host/group vars are the source of truth for infrastructure metadata,
- `plan` and `apply` run Ansible playbooks for lifecycle + day-2 convergence,
- lifecycle and configuration are fully Ansible-driven.

## Core Commands

```bash
proxmox-compose doctor --workspace .
proxmox-compose inventory sync --workspace .
proxmox-compose plan --workspace .
proxmox-compose apply --workspace .
proxmox-compose provision-existing --workspace .
```

## Profile Example

```yaml
profiles:
  default:
    ssh_key_path: ~/.ssh/id_ed25519
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
      PROXMOX_TOKEN_ID: ansible@pve!proxmox-compose
      PROXMOX_INSECURE: "true"
    secret_env_commands:
      PROXMOX_TOKEN_SECRET: "pass homelab/proxmox_token_secret"
```

## Scaffold Layout (after `init`)

- `config/ansible/playbooks/provision-infra.yml` - Ansible lifecycle reconciliation entrypoint.
- `config/ansible/playbooks/post-provision.yml` - day-2 base roles for provisioned hosts.
- `config/ansible/playbooks/provision-existing.yml` - brownfield host convergence.
- `config/ansible/inventory/static.yml` - tracked inventory groups.
- `config/ansible/inventory/host_vars/` and `group_vars/` - host metadata and app/service config.
- `docs/ansible-infra-model.md` - inventory schema and lifecycle contract.

## Validation

**Contributors (this CLI repo):**

```bash
PYTHONPATH=cli/src python -m pytest cli/tests -q
( cd cli/src/proxmox_compose/scaffold_assets/config/ansible && ansible-playbook -i inventory/static.yml playbooks/provision-infra.yml --syntax-check )
( cd cli/src/proxmox_compose/scaffold_assets/config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check )
```

**Your scaffolded workspace:**

```bash
proxmox-compose doctor --workspace .
proxmox-compose plan --workspace .
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/provision-infra.yml --syntax-check
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
```
