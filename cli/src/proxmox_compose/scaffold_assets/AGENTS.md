# AGENTS

This repository uses `proxmox-compose` as the primary interface.

## Core Workflow
1. Define hosts and lifecycle metadata in `config/ansible/inventory/static.yml` and `host_vars/`.
2. Run `proxmox-compose doctor`.
3. Run `proxmox-compose plan`.
4. Run `proxmox-compose apply`.
5. For pre-existing hosts, run `proxmox-compose provision-existing`.

## Platform Rules
- VM OS support: Debian, Fedora.
- LXC OS support: Debian only.
- Docker Compose apps run on VMs by default.
- Stateful services on LXCs should run under systemd units.

## Decision Matrix
- **Create/update VM or LXC lifecycle**: use `provision-infra.yml` via `proxmox-compose apply`.
- **Install packages/users/services on existing machine**: use Ansible roles/playbooks.
- **Deploy/update Docker Compose app on VM**: use `vm_docker` + `deploy_git_app`.
- **Deploy/update Docker Compose app on Debian LXC**: use `lxc_docker` + `lxc_compose_apps` (same keys as `vm_compose_apps`). Apply Proxmox host AppArmor workaround if Docker fails (`docs/lxc-docker-compose.md`).
- **Deploy/update non-Docker app in Debian LXC**: use `lxc_systemd_service`.
- **Manage pre-existing infrastructure**: inventory in `existing_hosts` / `existing_docker_vms` + `provision-existing`.
- **Inject secrets (`.env`, keys, tokens)**: Ansible Vault values consumed by host/group vars.
- **Expose a VM/LXC service on the tailnet or via Funnel**: opt-in `tailscale` role + `tailscale_serve` (see `docs/tailscale-on-lxc.md`).

## Existing Host Approaches
- **Git-managed app**: set `repo`, `dest`, optional `version`, and run compose.
- **Inline compose-managed app**: set `compose_file_content` and `env_content`.
- **Hybrid**: git checkout + override env (`env_content`) when needed.
- **No compose update desired**: set `compose: false` and use role for repo sync only.

## Frigate Update Path (Example Pattern)
1. Put host in `existing_docker_vms`.
2. Define host vars in `config/ansible/inventory/host_vars/<host>.yml` with compose content or repo source.
3. Store `.env` payload in encrypted vault vars (for example `frigate_env_content`).
4. Change image tag in compose definition.
5. Run `proxmox-compose provision-existing`.

## Safety and Idempotency
- Prefer declarative file updates over ad-hoc shell commands.
- Never hardcode real host IPs, usernames, or private paths in committed templates.
- Keep generated/runtime artifacts out of git (`build/`, `*.egg-info`).
- Avoid destructive operations unless explicitly requested.
- Keep changes minimal and scoped; preserve user edits outside task scope.

## Validation Checklist
- Run `proxmox-compose doctor` before plan/apply.
- For Python changes: run `pytest` and compile checks.
- For Ansible changes: run syntax check from `config/ansible`.

## Troubleshooting Playbook
- **Doctor fails**: install missing binary or profile vars.
- **Ansible role not found**: run from `config/ansible` and ensure `roles_path = ./roles`.
- **Inventory drift**: run `proxmox-compose inventory sync`.

## Where To Extend
- Add lifecycle behaviors: `config/ansible/roles/proxmox_lifecycle`.
- Add host config: `config/ansible/roles`.
- Add app rollouts: `config/ansible/roles/deploy_git_app`.
