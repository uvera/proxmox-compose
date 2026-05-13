# CLAUDE

When assisting in **this** repository, remember that it is primarily the **CLI and scaffold sources**, not a live Proxmox workspace: scaffold templates live under `cli/src/proxmox_compose/scaffold_assets/`. Product behavior for users still follows the rules below for **their** generated repos.

## Architecture Boundaries
- Ansible inventory + vars own lifecycle metadata for VMs and LXCs.
- Ansible owns OS/app configuration and day-2 operations.
- Keep lifecycle orchestration in Ansible playbooks/roles rather than custom Python state engines.

## Supported Matrix
- VM operating systems: Debian, Fedora.
- LXC operating systems: Debian only.
- Docker Compose workloads should default to VMs.
- LXC workloads should default to systemd services.

## Approach Selection
- Use `apply` for lifecycle reconciliation (`provision-infra.yml`) and post-provision converge.
- Use `provision-existing` for brownfield/existing machines.
- Use host vars for per-host compose and `.env` behavior.
- Use vault-backed variables for secrets material.
- For Tailscale Serve/Funnel on VMs or Debian LXCs, use the opt-in `tailscale` role (`tailscale_enable`, `tailscale_serve`); see scaffold `docs/tailscale-on-lxc.md`.

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
- Run `doctor` before orchestration commands in a **provisioned workspace** (not required for CLI-only edits in this repository).
- Keep inventory synchronized when editing inventory metadata.
- Validate changes: in this repo, run Python tests and Ansible checks against `cli/src/proxmox_compose/scaffold_assets/`; in a user workspace, run checks against `config/ansible`.
- If a task is environment-specific, implement as host_vars examples, not committed personal defaults.
