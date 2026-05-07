GUIDANCE_SCAFFOLD_FILES: dict[str, str] = {
    ".cursor/rules/proxmox-compose.mdc": """---
description: Proxmox Compose infrastructure and agent rules
alwaysApply: true
---

# Proxmox Compose Rule

- Treat Terraform as source of truth for VM/LXC lifecycle.
- Treat Ansible as source of truth for software and day-2 config.
- Support Debian and Fedora VMs; support Debian-only LXCs.
- Prefer VM deployment for Docker Compose workloads (for example Frigate).
- For LXC app workloads, use systemd units and explicit package/runtime dependencies.
- Never perform destructive Proxmox operations unless user explicitly requests it.
- Keep inventory synced before running Ansible against provisioned resources.
- Use `provision-existing` for brownfield hosts instead of forcing Terraform ownership.
- Prefer host_vars/group_vars patterns over hardcoded host-specific values in tracked files.
- Keep examples public-safe (no private IPs, usernames, tokens, or personal paths).
- For compose apps, support both git-based and inline `compose_file_content` approaches.
- Inject secrets via vault-backed variables and avoid plaintext credentials in repository.
- Validate with doctor/tests/syntax checks before proposing completion.
""",
    "AGENTS.md": """# AGENTS

This repository uses `proxmox-compose` as the primary interface.

## Core Workflow
1. Update desired infra in `infra/terraform/environments/homelab`.
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
- **Create/delete/resize VM or LXC**: use Terraform (`infra/terraform/**`).
- **Install packages/users/services on existing machine**: use Ansible roles/playbooks.
- **Deploy/update Docker Compose app on VM**: use `vm_docker` + `deploy_git_app`.
- **Deploy/update app in Debian LXC**: use `lxc_systemd_service`.
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
- Run `proxmox-compose doctor` before plan/apply.
- For Python changes: run `pytest` and compile checks.
- For Ansible changes: run syntax check from `config/ansible`.
- For Terraform changes: run `terraform fmt`, `terraform init -backend=false`, `terraform validate`.

## Troubleshooting Playbook
- **Doctor fails**: install missing binary or profile vars.
- **Ansible role not found**: run from `config/ansible` and ensure `roles_path = ./roles`.
- **Terraform provider mismatch**: ensure modules declare `required_providers` (`bpg/proxmox`).
- **Inventory drift**: run `proxmox-compose inventory sync`.

## Where To Extend
- Add new VM/LXC shape: `infra/terraform/modules`.
- Add host config: `config/ansible/roles`.
- Add app rollouts: `config/ansible/roles/deploy_git_app`.
""",
    "CLAUDE.md": """# CLAUDE

When assisting in this repository:

## Architecture Boundaries
- Terraform owns lifecycle state for VMs and LXCs.
- Ansible owns OS/app configuration and day-2 operations.
- Do not reimplement IaC state logic in custom Python.

## Supported Matrix
- VM operating systems: Debian, Fedora.
- LXC operating systems: Debian only.
- Docker Compose workloads should default to VMs.
- LXC workloads should default to systemd services.

## Approach Selection
- Use `apply` for newly provisioned resources and post-provision converge.
- Use `provision-existing` for brownfield/existing machines.
- Use host vars for per-host compose and `.env` behavior.
- Use vault-backed variables for secrets material.

## Secrets and Sensitive Data
- Never commit real secrets, API keys, or host-private credentials.
- Keep examples generic and reusable.
- Prefer encrypted Ansible vault data for `.env` contents and deploy keys.
- Use `no_log: true` for secret-copy tasks.

## Operational Safety
- Favor idempotent role/task changes.
- Avoid destructive actions unless explicitly requested by user.
- Do not hardcode user-specific hostnames, IPs, usernames, or home paths in templates.
- Keep repository public-safe by default.

## Execution Discipline
- Run `doctor` before orchestration commands.
- Keep inventory synchronized when mixing Terraform + static hosts.
- Validate changes (Terraform fmt/init/validate, Ansible syntax check, Python tests).
- If a task is environment-specific, implement as host_vars examples, not committed personal defaults.
""",
}

