# VM Service Onboarding

Use this flow for VM docker-compose apps (for example Frigate):

1. Define VM lifecycle input under `proxmox_lifecycle_vms` (typically in `group_vars` or host-specific vars consumed by `provision-infra.yml`).
2. Set host metadata in `config/ansible/inventory/host_vars/<host>.yml`:
   - `proxmox_compose_host_kind: vm`
   - `proxmox_compose_host_os: debian` or `fedora`
   - `ansible_host` / `ansible_user`
3. Run `proxmox-compose apply` to reconcile lifecycle and regenerate inventory.
4. Set `vm_compose_apps` host/group vars with repo and destination. For private **HTTPS** GitHub repos, set per-app `git_token` (vault-backed) or rely on group_vars / profile env — see `docs/secrets-and-ci.md` and `inventory/host_vars/example_existing_docker_vm.yml`.
5. Re-run `proxmox-compose apply` after app changes.

`vm_compose_apps` uses the same `deploy_git_app` role as `lxc_git_apps`, so optional `post_deploy_commands`, `restart_services`, and managed-file `restart_service` are available here too. See [lxc-service-onboarding.md](lxc-service-onboarding.md) for the full example. For Compose stacks, `restart_compose` remains the usual hook when a managed file should bounce containers.
