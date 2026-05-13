# Ansible Infrastructure Model

This scaffold uses an inventory-first infrastructure model.

## Sources of Truth

- `config/ansible/inventory/static.yml` defines tracked inventory groups.
- `config/ansible/inventory/host_vars/<host>.yml` defines host metadata.
- `config/ansible/inventory/group_vars/**/*.yml` defines shared lifecycle defaults and secrets references.

`proxmox-compose inventory sync` builds `inventory/generated.yml` and `inventory/hosts.yml` from those files.

## Host Metadata Contract

For inventory synthesis, each host can define:

- `proxmox_compose_host_kind`: `vm`, `lxc`, `existing`, or `existing_docker_vm`
- `proxmox_compose_host_os`: `debian` or `fedora` (used for `vm`)
- `proxmox_compose_inventory_group`: optional explicit override
- `ansible_host`, `ansible_user`

Group inference defaults:

- `vm` + `fedora` -> `fedora_vms`
- `vm` + any other OS -> `debian_vms`
- `lxc` -> `debian_lxcs`
- `existing` -> `existing_hosts`
- `existing_docker_vm` -> `existing_docker_vms`

## Lifecycle Definitions

`config/ansible/roles/proxmox_lifecycle` reconciles lifecycle entries from:

- `proxmox_lifecycle_vms`
- `proxmox_lifecycle_lxcs`

Each entry must provide `module_args`, which are passed to:

- `community.general.proxmox_kvm` (VMs)
- `community.general.proxmox` (LXCs)

Destructive actions (`state: absent`) are blocked unless `proxmox_lifecycle_allow_absent: true`.

## Command Flow

- `proxmox-compose plan`
  - `inventory sync`
  - Ansible `--check` on `playbooks/provision-infra.yml`
  - Ansible `--check` on `playbooks/post-provision.yml`
- `proxmox-compose apply`
  - `inventory sync`
  - Ansible run on `playbooks/provision-infra.yml`
  - Ansible run on `playbooks/post-provision.yml`
- `proxmox-compose provision-existing`
  - `inventory sync`
  - Ansible run on `playbooks/provision-existing.yml`
