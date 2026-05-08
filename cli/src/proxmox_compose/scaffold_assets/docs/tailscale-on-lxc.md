# Tailscale on Debian LXC (and VMs)

Run the Tailscale daemon **on the guest** (not only inside Docker) so you can use **Tailscale Serve** and **Funnel** to publish services—useful alongside `lxc_docker` / `vm_docker` when a Compose stack binds to `127.0.0.1` or a local port.

Scaffold support:

- Ansible role `tailscale` (opt-in via `tailscale_enable: true`).
- Declarative `tailscale_serve` list reconciled with `tailscale serve` / `tailscale funnel` (CLI 1.52+).
- Example host vars: `config/ansible/inventory/host_vars/example_lxc_tailscale.yml`.

## 1. Secrets and host variables

1. Put a pre-approved Tailscale auth key in encrypted `group_vars/all/vault.yml` as `tailscale_authkey` (see `vault.example.yml`).
2. In `host_vars` (or `group_vars`) set:

   ```yaml
   tailscale_enable: true
   tailscale_tags: ["tag:funnel"]   # optional; match your tailnet policy
   tailscale_serve:
     - port: 443
       protocol: https
       target: "http://127.0.0.1:8080"
       mount: "/"
       funnel: true                    # false = tailnet-only Serve
   ```

3. Run `proxmox-compose apply` (greenfield) or `proxmox-compose provision-existing` (brownfield). The `tailscale` role is included from `post-provision.yml` / `provision-existing.yml` but **no-ops** unless `tailscale_enable` is true.

## 2. Kernel TUN inside an unprivileged LXC

Tailscale on Linux expects a working **`/dev/net/tun`**. Unprivileged Proxmox LXCs do **not** get TUN by default. The Terraform provider used in this scaffold does **not** expose `lxc.cgroup2.devices.allow` or `lxc.mount.entry`, so this is a **one-time change on each Proxmox node** (same idea as the AppArmor note in [lxc-docker-compose.md](lxc-docker-compose.md)).

### Deployment-integrated hypervisor automation (optional)

When `lxc_host_config_enable: true`, deployment playbooks run role `lxc_host_config` before `tailscale`.
Enable `lxc_tun_enable: true` to patch these lines on the Proxmox node:

- `lxc.cgroup2.devices.allow: c 10:200 rwm`
- `lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file`

Set `lxc_host_config_restart: true` if you also want the CT restarted when those lines were newly added.

### Manual steps on the Proxmox host

For CT **vmid**:

1. `pct stop <vmid>`
2. Append to `/etc/pve/lxc/<vmid>.conf` on the Proxmox host:

   ```text
   lxc.cgroup2.devices.allow: c 10:200 rwm
   lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
   ```

3. `pct start <vmid>`

Inside the guest, `/dev/net/tun` should exist before convergence. The `tailscale` role asserts this when `ansible_virtualization_type` is `lxc`, unless **`tailscale_userspace: true`**.

### Userspace networking (optional)

When **`tailscale_userspace: true`**, the role skips the `/dev/net/tun` assertion on LXCs, configures Debian **`/etc/default/tailscaled`** with **`FLAGS="--tun=userspace-networking"`**, and passes **`tailscale up --tun=userspace-networking --netfilter-mode=off`**. Automating userspace on non-Debian guests is not supported in this scaffold (assert fails).

## 3. Funnel policy and limits

Funnel requires (Tailscale docs):

- **MagicDNS** enabled for the tailnet.
- **HTTPS** enabled with valid certificates for the tailnet DNS name.
- A **`funnel` `nodeAttrs`** entry in your ACL/policy allowing the tagging/user principal you use (often via `tailscale_tags` like `tag:funnel`).
- **Listener ports** restricted to **443**, **8443**, or **10000** for Funnel.

The role validates Funnel ports when `funnel: true`. Serve-only rules may use other ports for `protocol: http` / `https` per Tailscale Serve docs.

## 4. Relationship to Docker Compose on the same LXC

Typical pattern:

1. Compose publishes `8080:80` on the **container loopback** or all interfaces; proxy target in `tailscale_serve` uses `http://127.0.0.1:8080`.
2. Tailscale terminates TLS on **443** (Funnel or tailnet HTTPS) and forwards to the local HTTP service.

If you bind the workload only to `127.0.0.1` in Compose, ensure that port matches `tailscale_serve` → `target`.

## 5. Further reading

- [Tailscale Serve (CLI)](https://tailscale.com/kb/1242/tailscale-serve/)
- [Tailscale Funnel](https://tailscale.com/kb/1223/tailscale-funnel/)
