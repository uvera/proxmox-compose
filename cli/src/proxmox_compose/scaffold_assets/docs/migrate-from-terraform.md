# Migrate From Terraform

Use this guide to migrate a Terraform-managed workspace to the Ansible-first model.

## 1) Pre-migration audit

- Export current VM/LXC metadata from Terraform outputs/state (`vmid`, `node`, IP/user).
- Inventory all hosts currently managed by Terraform:
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

## 3) Map Terraform outputs to Ansible vars

- `outputs.vms.<host>.ansible_host` -> `host_vars/<host>.yml: ansible_host`
- `outputs.vms.<host>.ansible_user` -> `host_vars/<host>.yml: ansible_user`
- `outputs.vms.<host>.os` -> `host_vars/<host>.yml: proxmox_compose_host_os`
- `outputs.debian_lxcs.<host>.vmid` -> `host_vars/<host>.yml: lxc_host_config_vmid`
- `outputs.debian_lxcs.<host>.node_name` -> `host_vars/<host>.yml: lxc_host_config_node_name`
- `outputs.proxmox_node_addresses` -> `lxc_host_config_node_addresses`
- `outputs.proxmox_ssh_username` -> `lxc_host_config_ssh_user` (optional)

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

- Stop using Terraform in day-to-day workflows.
- Keep Terraform files as archive/rollback material until you complete one stable cycle.
- Remove Terraform-specific CI checks and docs in your migrated repo.

## Rollback plan

If cutover fails:

1. Restore the previous inventory and host/group vars from git.
2. Re-enable Terraform-driven workflow and rerun `plan/apply` in the old model.
3. Compare host connectivity and service health.
4. Retry migration host-by-host rather than all-at-once.
