# Debian LXC Service Onboarding

For **Docker Compose on an LXC** (instead of systemd apps), see [lxc-docker-compose.md](lxc-docker-compose.md).

To run **Tailscale Serve or Funnel on the same Debian LXC** (native `tailscaled` alongside Compose or systemd workloads), see [tailscale-on-lxc.md](tailscale-on-lxc.md).

Use this flow for Debian LXC systemd workloads:
1. Define LXC lifecycle input under `proxmox_lifecycle_lxcs` (group vars or host vars consumed by `provision-infra.yml`).
2. Set host metadata in `config/ansible/inventory/host_vars/<host>.yml`:
   - `proxmox_compose_host_kind: lxc`
   - `proxmox_compose_host_os: debian`
   - `ansible_host` / `ansible_user`
3. Define `lxc_packages` and `lxc_git_apps` as needed.
4. Optional: set `go_install_path` on a `lxc_git_apps` entry to compile a Go module after `git` checkout.
   Optional: set `go_version` (for example `1.25.0`) when building **on the LXC** (`lxc_go_build_local: false`) to bootstrap that toolchain from go.dev.
   By default `lxc_go_build_local` is true (see `group_vars/all/main.yml`): Go binaries build on the Ansible controller and are copied to the LXC (install `go` on the machine running Ansible). Set `lxc_go_build_local: false` to compile on the guest instead.
5. Optional (any git app): set `post_deploy_commands` on a `lxc_git_apps` / `deploy_git_app` entry to run argv-style commands after checkout (see below).
   Optional: set `restart_services` on the git app entry (list of systemd unit names) to bounce those units after a checkout or managed-file change — for example to reload a PHP-FPM pool so opcache picks up new code.
   Optional: set `restart_service` on a `managed_files` entry to restart a systemd unit when that file changes.
6. Optional: define `lxc_system_users` (`name`, optional `group` / `shell` / `system` / `create_home` / `home`) so the app OS user exists **before** git checkout. `deploy_git_app` creates declared groups, not users; `post_deploy_commands` run as `owner` via `su` and need a login shell.
7. Optional (Python apps): define `lxc_python_apps` entries to create a venv, install editable dependencies, and run migrations.
   Optional: set `extras: ["daemon", "..."]` on a `lxc_python_apps` entry to install PEP 508 extras (renders as `pip install -e "<app_dir>[extra1,extra2]"`).
8. Optional: define `lxc_runtime_dirs` entries (`path`, `owner`, `group`, `mode`) for state / cache / output directories the service user must own (created before git checkout and before the unit starts; use for paths referenced in `EnvironmentFile=`).
9. Optional: define `lxc_systemd_overrides` entries (`unit`, optional `filename`, `content`) to write a systemd drop-in under `/etc/systemd/system/<unit>.d/` and restart `<unit>` when it changes — use this to make a package-provided unit reboot-safe when it depends on a tmpfs path that `systemd-tmpfiles` may not have recreated yet (see example below).
10. Define `lxc_systemd_services` entries with `exec_start`; optional `environment_file` / `environment_files` for systemd `EnvironmentFile=`.
11. Re-run `proxmox-compose apply`.

## Native PHP (or other non-Docker) git apps

`lxc_git_apps` is passed through role `deploy_git_app` with compose disabled. Use that for a git checkout plus optional config files and a post-checkout command hook — for example a Laravel/Filament app with PHP-FPM + Caddy + PostgreSQL (no Docker).

`post_deploy_commands` is a list of command strings, run in order with `chdir` set to the app `dest`. Each command is `ansible.builtin.command` (not `shell`): no pipes, redirects, or `&&`. Prefer a repo script such as `./deploy/deploy.sh`.

Commands run **as the entry's `owner`** (default `root`) via `become_method: su` (`deploy_git_app_post_deploy_become_method`; override per app with `post_deploy_become_method`). They run only when that app's git checkout **or** any of its `managed_files` actually changed. Set `post_deploy_no_log: true` when command output could leak secrets.

`deploy_git_app` creates declared **groups**, not users. Declare the app user in `lxc_system_users` (login shell required for `su`). On guests that have sudo instead of a usable `su` path, set `post_deploy_become_method: sudo`. When `owner` is set, the checkout tree is chowned to that user after `git` so the hook can write `vendor/` and caches.

`restart_services` on the git app entry is a list of systemd unit names restarted after post-deploy when checkout or managed files changed (use this to reload a PHP-FPM pool for opcache on code updates).

`restart_service` on a `managed_files` entry is a single systemd unit name (parallel to Compose-only `restart_compose`). It restarts that unit when the file content changes. To bounce two units from file changes, use two `managed_files` entries.

PostgreSQL `lxc_postgresql_role_updates` creates the role if it does not exist, otherwise `ALTER ROLE` (password + `LOGIN`).

For Tailscale Serve, bind Caddy (or another local reverse proxy) to loopback HTTP (for example `http://127.0.0.1:8080`) and let `tailscale_serve` terminate HTTPS — do not have Caddy listen on 443. See [tailscale-on-lxc.md](tailscale-on-lxc.md).

```yaml
lxc_system_users:
  - name: myapp
    group: myapp
    system: true
    shell: /bin/bash

lxc_packages:
  - php-fpm
  - php-pgsql
  - composer
  - caddy
  - postgresql

lxc_git_apps:
  - dest: /opt/myapp
    repo: https://github.com/example/myapp.git
    version: main
    owner: myapp
    group: myapp
    post_deploy_commands:
      - ./deploy/deploy.sh
    restart_services:
      - php8.3-fpm
    managed_files:
      - dest: /etc/php/8.3/fpm/pool.d/myapp.conf
        owner: root
        group: root
        mode: "0644"
        content: |
          [myapp]
          user = myapp
          group = myapp
          listen = /run/php/myapp.sock
        restart_service: php8.3-fpm
      - dest: /etc/caddy/Caddyfile
        owner: root
        group: root
        mode: "0644"
        content: |
          http://:8080 {
              bind 127.0.0.1
              root * /opt/myapp/public
              php_fastcgi unix//run/php/myapp.sock
              file_server
          }
        restart_service: caddy
```

The same `post_deploy_commands`, `restart_services`, and `restart_service` fields work on `vm_compose_apps` / `lxc_compose_apps` (they share `deploy_git_app`).

## Reboot-safe systemd unit overrides

Some package-provided units depend on a tmpfs path (for example `/run/php`) that `systemd-tmpfiles` does not reliably recreate before the unit starts inside an LXC across reboots. `lxc_systemd_overrides` writes a drop-in and restarts the unit when its content changes:

```yaml
lxc_systemd_overrides:
  - unit: php8.3-fpm.service
    content: |
      [Service]
      ExecStartPre=/usr/bin/install -d -o myapp -g myapp -m 0755 /run/php
```

`content` is written to `/etc/systemd/system/<unit>.d/override.conf` (or `filename` if set); systemd is reloaded and `<unit>` restarted only when the drop-in content changes.
