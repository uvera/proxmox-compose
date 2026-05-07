# AGENTS

This git repository is the **`proxmox-compose` CLI** and embedded scaffold templates. There is no `infra/` or `config/ansible/` at this repository root; those paths exist in **repositories created with** `proxmox-compose init`.

## Maintaining this CLI repository
1. Edit Python under `cli/src/proxmox_compose/`.
2. Edit Terraform/Ansible/docs templates under `cli/src/proxmox_compose/scaffold_assets/` (see `.cursor/rules/scaffold-sync.mdc`).
3. Run `PYTHONPATH=cli/src pytest cli/tests` and Terraform/Ansible checks against the scaffold tree (see `docs/secrets-and-ci.md` or `.github/workflows/validate.yml`).

## Core workflow (in a provisioned workspace)
1. Update desired infra in `infra/terraform/environments/homelab`.
2. Run `proxmox-compose doctor`.
3. Run `proxmox-compose plan`.
4. Run `proxmox-compose apply`.
5. For pre-existing hosts, run `proxmox-compose provision-existing`.

## Platform Rules
- VM OS support: Debian, Fedora.
- LXC OS support: Debian only.
- Docker Compose apps run on VMs by default; optional Compose on LXCs via `lxc_docker`.
- Stateful native services on LXCs often use `lxc_systemd_service`; Compose stacks can use `lxc_docker`.

## Decision Matrix
- **Create/delete/resize VM or LXC**: use Terraform (`infra/terraform/**`).
- **Install packages/users/services on existing machine**: use Ansible roles/playbooks.
- **Deploy/update Docker Compose app on VM**: use `vm_docker` + `deploy_git_app`.
- **Deploy/update Docker Compose app on Debian LXC**: use `lxc_docker` + `lxc_compose_apps` (see scaffold `docs/lxc-docker-compose.md`).
- **Deploy/update non-Docker app in Debian LXC**: use `lxc_systemd_service`.
- **Manage pre-existing infrastructure**: inventory in `existing_hosts` / `existing_docker_vms` + `provision-existing`.
- **Inject secrets (`.env`, keys, tokens)**: Ansible Vault values consumed by host/group vars.

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
- Keep generated/runtime artifacts out of git (`build/`, `*.egg-info`, `.terraform/`).
- Avoid destructive operations unless explicitly requested.
- Keep changes minimal and scoped; preserve user edits outside task scope.

## Validation Checklist
- Run `proxmox-compose doctor` before plan/apply (in a provisioned workspace).
- For Python changes in this repo: `PYTHONPATH=cli/src pytest cli/tests`.
- For Ansible template changes: syntax check from `cli/src/proxmox_compose/scaffold_assets/config/ansible`.
- For Terraform template changes: `terraform fmt` / `terraform validate` on `cli/src/proxmox_compose/scaffold_assets/infra/terraform`.

## Troubleshooting Playbook
- **Doctor fails**: install missing binary or profile vars.
- **Ansible role not found**: run from `config/ansible` and ensure `roles_path = ./roles`.
- **Terraform provider mismatch**: ensure modules declare `required_providers` (`bpg/proxmox`).
- **Inventory drift**: run `proxmox-compose inventory sync`.

## Where To Extend
- Add new VM/LXC shape: `cli/src/proxmox_compose/scaffold_assets/infra/terraform/modules` (and generated repos: `infra/terraform/modules`).
- Add host config: `cli/src/proxmox_compose/scaffold_assets/config/ansible/roles` (generated: `config/ansible/roles`).
- Add app rollouts: `cli/src/proxmox_compose/scaffold_assets/config/ansible/roles/deploy_git_app`.
