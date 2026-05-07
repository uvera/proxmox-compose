# Debian LXC + Docker Compose

Use this path when you want **Docker Compose on an unprivileged Debian LXC** instead of a VM or instead of native systemd services (`lxc_systemd_service`).

## 1. Proxmox / Terraform

- **Nesting** — Required for Docker inside LXC. The scaffold `lxc-debian` module sets `features.nesting = true` by default.
- **Optional features** — If an image or runtime needs them, set per-LXC in Terraform (`debian_lxcs` entries):
  - `lxc_features_fuse: true` — FUSE inside the CT (some stacks need it).
  - `lxc_features_keyctl: true` — Rare; only if something explicitly requires `keyctl`.
- **Lifecycle note** — The module uses `lifecycle { ignore_changes = [features] }` so existing CTs keep working when API tokens cannot change feature flags. New CTs still get the declared flags at create time.

The [bpg/proxmox](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_container) provider does **not** expose `lxc.apparmor.profile` or raw `/etc/pve/lxc/<vmid>.conf` lines. Those are applied on the **Proxmox host**, not from Terraform in this scaffold.

## 2. AppArmor / runc (CVE-2025-52881)

Recent `runc` / `containerd` updates can break Docker/Podman **inside** Proxmox LXCs with AppArmor errors (for example permission denied when reopening sysctl-related fds). See [opencontainers/runc#4968](https://github.com/opencontainers/runc/issues/4968).

**Do not downgrade `runc`** to avoid the bug — that reintroduces security issues the updates fixed.

**Workaround (on each Proxmox node, for each CT VMID):**

1. Stop the container: `pct stop <vmid>`
2. Edit `/etc/pve/lxc/<vmid>.conf` on the Proxmox host and add at the end:
   - **All distributions (including Debian):**
     ```text
     lxc.apparmor.profile: unconfined
     ```
   - **Ubuntu templates only** (additional line):
     ```text
     lxc.mount.entry: /dev/null sys/module/apparmor/parameters/enabled none bind 0 0
     ```
3. Start the container: `pct start <vmid>`

Automation helpers (same idea, optional): [jq6l43d1/proxmox-lxc-docker-fix](https://github.com/jq6l43d1/proxmox-lxc-docker-fix).

This relaxes AppArmor confinement for that CT only; the CT remains **unprivileged**, which is still the main isolation boundary. Use VMs if you need stronger isolation.

## 3. Ansible: git / inline Compose on the LXC

Same variable shape as VM Compose (`vm_compose_apps`), but use **`lxc_compose_apps`** in host vars (or group vars) for LXCs.

1. Ensure the host is in inventory group `debian_lxcs` (Terraform sync / static inventory).
2. Create `config/ansible/inventory/host_vars/<host>.yml` — see `inventory/host_vars/example_lxc_docker.yml`.
3. Set `lxc_compose_apps` with `repo` + `dest`, or `compose_file_content`, optional `env_content`, etc. (identical keys to `example_existing_docker_vm.yml`).
4. Optional: `lxc_docker_enable: true` installs Docker even when `lxc_compose_apps` is empty (manual compose projects).
5. Run `proxmox-compose apply` (greenfield) or `proxmox-compose provision-existing` (brownfield).

The `lxc_docker` role installs `docker.io` and `docker-compose-plugin` on Debian and includes `deploy_git_app` for stacks.

## 4. When to prefer a VM

For heavy or security-sensitive Compose workloads, the project still defaults to **VMs** (`vm_docker`): simpler device passthrough and stronger isolation. LXCs are appropriate when you accept CT trade-offs and apply nesting + (if needed) the AppArmor workaround above.
