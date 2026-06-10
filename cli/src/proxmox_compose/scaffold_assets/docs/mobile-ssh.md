# Mobile SSH via NovaAccess

SSH into LXCs from your phone using [NovaAccess](https://galaxnet.dev/nova/) (built-in tailnet + SSH terminal). This scaffold manages **SSH public keys** declaratively and joins each LXC to your tailnet.

Tailscale SSH (`tailscale_ssh: true`) is **not** used — NovaAccess authenticates with normal OpenSSH keys over the tailnet.

## Prerequisites

1. Tailscale auth key in encrypted `group_vars/all/vault.yml` as `tailscale_authkey` (see [tailscale-on-lxc.md](tailscale-on-lxc.md)).
2. Each LXC: `tailscale_enable: true` and `lxc_tun_enable: true` (unprivileged CTs need kernel TUN on the Proxmox host).
3. `ansible.posix` collection installed on the Ansible controller:

   ```bash
   ansible-galaxy collection install -r config/ansible/collections/requirements.yml
   ```

## SSH public key array

Keys are merged from three sources in [`group_vars/all/main.yml`](../config/ansible/inventory/group_vars/all/main.yml):

| Variable | Where | Purpose |
|----------|-------|---------|
| `ssh_authorized_keys_base` | `group_vars/all` | Desktop/Ansible key (`proxmox_compose_lxc_pubkey`) |
| `ssh_authorized_keys_extra` | group or `host_vars` | Optional plain-text extras |
| `ssh_authorized_keys_vault` | encrypted `vault.yml` | Operator/device keys (NovaAccess phone, tablet, …) |

Role `common` reconciles the merged `ssh_authorized_keys` list into `~/.ssh/authorized_keys` with `exclusive: true` — removed inventory entries are pruned on converge.

### Add a NovaAccess phone key

1. In NovaAccess: **Settings → Keys → Generate Key** (ed25519). Copy the public key.
2. Add to vault:

   ```bash
   proxmox-compose vault edit --workspace .
   ```

   ```yaml
   ssh_authorized_keys_vault:
     - "ssh-ed25519 AAAA... novaaccess-phone"
   ```

3. Converge (inventory LXCs use `apply`, not `provision-existing`):

   ```bash
   proxmox-compose apply --workspace .
   ```

### Revoke or rotate a key

Edit `ssh_authorized_keys_vault` (remove old / add new pubkey), then `proxmox-compose apply --workspace .`.

## NovaAccess host setup (phone)

Sign into your tailnet in NovaAccess. Add one SSH host per LXC using **MagicDNS** names (not LAN IPs):

| Display name | Host | User | Key |
|--------------|------|------|-----|
| my-lxc | `my-lxc` | `root` | your NovaAccess key |
| app-lxc | `app-lxc` | `root` | same |

NovaAccess can also browse internal HTTPS services (Caddy-proxied apps, CUPS) over the same tailnet.

## Per-host overrides

Append keys on one host only:

```yaml
# host_vars/example.yml
ssh_authorized_keys_extra:
  - "ssh-ed25519 AAAA... deploy-bot"
```

Replace the full merged list on a host (advanced):

```yaml
ssh_authorized_keys:
  - "ssh-ed25519 AAAA... only-on-this-host"
```

## USB-dependent LXCs

For LXCs that depend on USB hardware (for example a CUPS print server), set `lxc_host_config_ensure_started: false` so Ansible does not auto-start/restart the CT when the device is unplugged, and **skips the post-provision SSH wait** during `apply` (other hosts are not blocked for five minutes). See [`example_provisioned_lxc.yml`](../config/ansible/inventory/host_vars/example_provisioned_lxc.yml) for the full pattern.

After the USB device is connected on the Proxmox host, start the CT and run:

```bash
proxmox-compose apply --workspace . --host my-print-server
```

## Related docs

- [tailscale-on-lxc.md](tailscale-on-lxc.md) — TUN, Serve/Funnel, tailnet join
- [secrets-and-ci.md](secrets-and-ci.md) — vault workflow
