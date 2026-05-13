# Migration Guide

Use this guide to migrate an existing workspace to the current inventory-first model.

## 1) Pre-migration audit

- Export current VM/LXC metadata (`vmid`, `node`, IP/user) from your existing source-of-truth.
- Inventory all managed hosts:
  - Debian VMs
  - Fedora VMs
  - Debian LXCs
- Capture app config from existing `host_vars`/`group_vars` and running services.

## 2) Create inventory metadata

For each host, create `config/ansible/inventory/host_vars/<host>.yml` with:

- `ansible_host`
- `ansible_user`
- `proxmox_compose_host_kind`
- `proxmox_compose_host_os` (for VMs)

For LXCs that use `lxc_host_config`, set:

- `lxc_host_config_vmid`
- `lxc_host_config_node_name`
- `lxc_host_config_node_addresses`

Optionally add explicit `proxmox_compose_inventory_group` when you do not want inferred grouping.

## 3) Map old metadata to inventory vars

- host address -> `host_vars/<host>.yml: ansible_host`
- host user -> `host_vars/<host>.yml: ansible_user`
- VM OS -> `host_vars/<host>.yml: proxmox_compose_host_os`
- LXC vmid -> `host_vars/<host>.yml: lxc_host_config_vmid`
- LXC node name -> `host_vars/<host>.yml: lxc_host_config_node_name`
- node address map -> `lxc_host_config_node_addresses`
- Proxmox SSH user -> `lxc_host_config_ssh_user` (optional)

## 4) Add lifecycle declarations

Move desired create/update actions into:

- `proxmox_lifecycle_vms`
- `proxmox_lifecycle_lxcs`

Each item should carry `module_args` compatible with the target Ansible module.

## 5) Dry-run and cutover

1. `proxmox-compose doctor --workspace .`
2. `proxmox-compose inventory sync --workspace .`
3. `proxmox-compose plan --workspace .`
4. Fix diffs/errors in vars and rerun plan.
5. `proxmox-compose apply --workspace .`

## 6) Cleanup

- Stop using old lifecycle tooling in day-to-day workflows.
- Keep old files as archive/rollback material until one stable cycle is complete.
- Remove old CI checks and docs from your migrated repo.

## Rollback plan

If cutover fails:

1. Restore the previous inventory and host/group vars from git.
2. Re-enable the previous workflow and rerun your normal converge command.
3. Compare host connectivity and service health.
4. Retry migration host-by-host rather than all-at-once.
