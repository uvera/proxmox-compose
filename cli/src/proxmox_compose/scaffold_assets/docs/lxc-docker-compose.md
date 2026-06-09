# Debian LXC + Docker Compose

Use this path when you want **Docker Compose on an unprivileged Debian LXC** instead of a VM or instead of native systemd services (`lxc_systemd_service`).

## 1. Proxmox lifecycle metadata

- **Nesting** — Required for Docker inside LXC. Set the corresponding Proxmox module args in `proxmox_lifecycle_lxcs`.
- **Optional features** — If an image or runtime needs them, set per-LXC module args:
  - `features.nesting: true` (recommended for Docker)
  - `features.fuse: true` (when required by workload)
  - `features.keyctl: true` (rare, only when explicitly needed)

Raw `/etc/pve/lxc/<vmid>.conf` lines (AppArmor/TUN tweaks) are applied on the **Proxmox host** through role `lxc_host_config`.

## 2. AppArmor / runc (CVE-2025-52881)

Recent `runc` / `containerd` updates can break Docker/Podman **inside** Proxmox LXCs with AppArmor errors (for example permission denied when reopening sysctl-related fds). See [opencontainers/runc#4968](https://github.com/opencontainers/runc/issues/4968).

**Do not downgrade `runc`** to avoid the bug — that reintroduces security issues the updates fixed.

**Workaround (applied on each Proxmox node, per CT VMID):**

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

### Deploy-time automation (opt-in Ansible)

During **`proxmox-compose apply`** and **`proxmox-compose provision-existing`**, the **`lxc_host_config`** role can apply the same `/etc/pve/lxc/<vmid>.conf` lines by SSH’ing from the Ansible **controller** to the Proxmox node (the profile **`ssh_key_path`** is passed as `ansible-playbook --private-key`, same as guest runs).

1. In `host_vars` or `group_vars`, set for example:

   ```yaml
   lxc_host_config_enable: true
   lxc_apparmor_unconfined_enable: true
   lxc_tun_enable: true
   lxc_host_config_restart: true
   # Ubuntu LXC templates only (not Debian):
   # lxc_apparmor_ubuntu_mask_enable: true
   ```

2. Provide host metadata in inventory vars (recommended):
   - `lxc_host_config_vmid`
   - `lxc_host_config_node_name`
   - `lxc_host_config_node_addresses`
   - optional `lxc_host_config_ssh_user` / `lxc_host_config_ssh_private_key_file`
3. Re-run **`proxmox-compose apply`** or **`proxmox-compose provision-existing`**.

### CT firewall (opt-in)

Role `lxc_host_config` can manage `/etc/pve/firewall/<vmid>.fw` on the Proxmox node. Enable the CT firewall in lifecycle `netif` (for example `firewall=1` on the veth line) and define rules in host vars:

```yaml
lxc_host_config_firewall_enable: true
lxc_host_config_firewall_rules:
  - "IN ACCEPT -p tcp -dport 22"
  - "IN ACCEPT -source 10.0.0.10 -p tcp -dport 8080"
  - "IN DROP -p tcp -dport 8080"
```

When `lxc_host_config_restart: true`, firewall file changes trigger a CT restart (same as conf-line changes). See `inventory/host_vars/example_lxc_firewall.yml`.

### Host-side udev rules (opt-in)

For USB or other device passthrough into an unprivileged LXC, you may need udev rules on the **Proxmox node** (not inside the CT). Role `lxc_host_config` can write `/etc/udev/rules.d/*` and reload udev:

```yaml
lxc_host_config_udev_rules:
  - name: 99-example-device.rules
    content: |
      SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ATTR{idProduct}=="5678", MODE="0666"
```

Pair with appropriate `lxc_host_config_extra_lines` bind mounts or cgroup device allowances for the target device.

## 3. Ansible: git / inline Compose on the LXC

Same variable shape as VM Compose (`vm_compose_apps`), but use **`lxc_compose_apps`** in host vars (or group vars) for LXCs.

1. Ensure the host is in inventory group `debian_lxcs` (from static inventory or host_vars metadata).
2. Create `config/ansible/inventory/host_vars/<host>.yml` — see `inventory/host_vars/example_lxc_docker.yml`.
3. Set `lxc_compose_apps` with `repo` + `dest`, or `compose_file_content`, optional `env_content`, etc. (identical keys to `example_existing_docker_vm.yml`).
4. Optional: `lxc_docker_enable: true` installs Docker even when `lxc_compose_apps` is empty (manual compose projects).
5. Run `proxmox-compose apply` (greenfield) or `proxmox-compose provision-existing` (brownfield).

The `lxc_docker` role installs `docker.io` and `docker-compose-plugin` on Debian and includes `deploy_git_app` for stacks.

### Optional: pre-pull images before `docker compose` convergence

During **`proxmox-compose apply`** or **`proxmox-compose provision-existing`**, the `deploy_git_app` role can pull or copy container images **before** it runs `community.docker.docker_compose_v2` (after repos, inline compose files, and env files are on disk).

In host or group vars:

- **`deploy_git_app_prepull`** — set `true` to run the pre-pull phase.
- **`deploy_git_app_prepull_method`** — `docker` runs `docker compose pull` in each app directory; `skopeo` runs `skopeo copy docker://… docker-daemon:…`. With **`skopeo`**, the role installs the **`skopeo`** package on Debian/Fedora targets (`ansible.builtin.package`); override the package name with **`deploy_git_app_skopeo_package_name`** if your distro differs.
- **`deploy_git_app_prepull_images`** — optional list of image references for **skopeo** mode, unioned with each app entry’s **`prepull_images`**. If the merged list is empty in skopeo mode, images are taken from `docker compose config --images`.
- **`deploy_git_app_prepull_force`** — when `true`, skopeo mode re-copies even if `docker image inspect` already succeeds.

There is no `proxmox-compose prepull` CLI command; pre-pull is only part of the Ansible role during normal runs. To refresh repos and env files **without** `docker_compose_v2`, pass extra var **`deploy_git_app_skip_compose=true`** (for example with ad-hoc `ansible-playbook`); image pre-pull still runs when **`deploy_git_app_prepull`** is enabled.

The same variables apply to **VM** Compose stacks (`vm_docker` → `deploy_git_app`), not only LXCs.

## 4. When to prefer a VM

For heavy or security-sensitive Compose workloads, the project still defaults to **VMs** (`vm_docker`): simpler device passthrough and stronger isolation. LXCs are appropriate when you accept CT trade-offs and apply nesting + (if needed) the AppArmor workaround above.

## 5. Tailscale Serve / Funnel on the same LXC

To run Tailscale **natively** on the LXC (alongside Docker) for Serve or Funnel, see [tailscale-on-lxc.md](tailscale-on-lxc.md) (kernel TUN on the Proxmox host, vault key, and `tailscale_serve` examples).
