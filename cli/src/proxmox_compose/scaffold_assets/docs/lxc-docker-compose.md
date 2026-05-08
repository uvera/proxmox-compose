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

1. Ensure **Terraform outputs** are available under `infra/terraform/environments/homelab` so the role can discover `debian_lxcs`, `proxmox_node_addresses`, and `proxmox_ssh_username` automatically.
2. In `host_vars` or `group_vars`, set for example:

   ```yaml
   lxc_host_config_enable: true
   lxc_apparmor_unconfined_enable: true
   lxc_tun_enable: true
   lxc_host_config_restart: true
   # Ubuntu LXC templates only (not Debian):
   # lxc_apparmor_ubuntu_mask_enable: true
   ```

3. Re-run **`proxmox-compose apply`** or **`proxmox-compose provision-existing`**.

For brownfield LXCs that are **not** in Terraform, set **`lxc_host_config_vmid`** and either
**`lxc_host_config_node_address`** or (**`lxc_host_config_node_name`** + `lxc_host_config_node_addresses`)
plus optional **`lxc_host_config_ssh_user`**.

## 3. Ansible: git / inline Compose on the LXC

Same variable shape as VM Compose (`vm_compose_apps`), but use **`lxc_compose_apps`** in host vars (or group vars) for LXCs.

1. Ensure the host is in inventory group `debian_lxcs` (Terraform sync / static inventory).
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
