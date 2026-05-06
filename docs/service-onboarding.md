# VM Service Onboarding

Use this flow for VM docker-compose apps (for example Frigate):
1. Add VM definition in Terraform vars.
2. Add host to `debian_vms` or `fedora_vms` inventory grouping.
3. Set `vm_compose_apps` host/group vars with repo and destination.
4. Re-run `proxmox-compose apply`.
