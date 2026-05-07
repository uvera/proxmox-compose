from pathlib import Path


SCAFFOLD_FILES: dict[str, str] = {
    ".gitignore": """.venv/
__pycache__/
*.pyc
.pytest_cache/

.terraform/
*.tfstate
*.tfstate.*
terraform.tfvars

config/ansible/group_vars/all/vault.yml
.cursor/plans/
""",
    "README.md": """# Proxmox Compose

Infrastructure-as-code for Proxmox with Terraform + Ansible, orchestrated by `proxmox-compose`.

## What It Does

- Provisions Proxmox **VMs** (Debian/Fedora) and **LXCs** (Debian only) with Terraform.
- Configures hosts and workloads with Ansible.
- Supports both:
  - greenfield provisioning (`plan` / `apply`)
  - brownfield convergence for existing hosts (`provision-existing`)
- Manages Docker Compose apps on VMs and systemd services on Debian LXCs.

## Install CLI (System-Wide)

```bash
pipx install ./cli
```

If already installed and you changed local code:

```bash
pipx install --force ./cli
```

## Core Commands

```bash
proxmox-compose --help
proxmox-compose doctor --workspace .
proxmox-compose plan --workspace .
proxmox-compose apply --workspace .
proxmox-compose provision-existing --workspace .
proxmox-compose inventory sync --workspace .
```

## Profile SSH Key and Encrypted Proxmox Credentials

You can set an SSH private key in your CLI profile so Ansible uses it for
`plan`, `apply`, and `provision-existing`, and resolve sensitive values from a
command instead of storing plaintext.

Recommended: API token ID + secret:

```yaml
profiles:
  default:
    ssh_key_path: ~/.ssh/id_ed25519
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "pass homelab/proxmox_token_secret"
    env:
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
      TF_VAR_proxmox_insecure: "true"
```

`secret_env_commands` supports either a shell-like string command or an argv
list, for example:

```yaml
secret_env_commands:
  TF_VAR_proxmox_token_secret:
    - op
    - read
    - op://Homelab/Proxmox/token_secret
```

## Recommended Workflow

1. Update desired infrastructure in `infra/terraform/environments/homelab`.
2. Run `proxmox-compose doctor --workspace .` to verify binaries/profile/files.
3. Run `proxmox-compose plan --workspace .`.
4. Run `proxmox-compose apply --workspace .`.
5. For pre-existing hosts, define inventory + vars and run:
   `proxmox-compose provision-existing --workspace .`.

## Repository Layout

- `infra/terraform/` - VM/LXC lifecycle and Terraform modules.
- `config/ansible/playbooks/` - orchestration playbooks.
- `config/ansible/roles/` - reusable host/app roles.
- `config/ansible/inventory/` - static + generated inventory.
- `config/ansible/host_vars/` - per-host overrides (existing host patterns).
- `config/ansible/group_vars/` - shared variables and vault references.
- `docs/` - onboarding and operational guidance.
- `.cursor/rules/`, `AGENTS.md`, `CLAUDE.md` - AI/agent guidance.

## Existing Host Compose Management

For existing Docker VMs:

1. Add host to `existing_hosts` and/or `existing_docker_vms` in
   `config/ansible/inventory/static.yml`.
2. Create `config/ansible/host_vars/<host>.yml` (see
   `config/ansible/host_vars/example_existing_docker_vm.yml`).
3. Choose approach:
   - git-based app (`repo` + `dest`)
   - inline compose (`compose_file_content`)
   - optional `.env` injection (`env_content`) from vault-backed variables
4. Run `provision-existing`.

To update Frigate image tag as code:
- edit image in host vars compose definition
- re-run `provision-existing`

## Secrets

- Keep secret values out of tracked files.
- Put sensitive vars into encrypted vault files (for example
  `config/ansible/group_vars/all/vault.yml`).
- Reference those values from host/group vars (for example `.env` content).

## Validation

Before pushing changes:

```bash
proxmox-compose doctor --workspace .
terraform fmt -check -recursive infra/terraform
cd infra/terraform/environments/homelab && terraform init -backend=false && terraform validate
cd ../../../..
cd config/ansible && ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
```
""",
    "Makefile": """PYTHON ?= python

.PHONY: install-cli test-cli lint-cli

install-cli:
\tpipx install --force ./cli

test-cli:
\tPYTHONPATH=cli/src $(PYTHON) -m pytest cli/tests -q

lint-cli:
\tPYTHONPATH=cli/src $(PYTHON) -m compileall cli/src
""",
    "infra/terraform/environments/homelab/providers.tf": """terraform {
  required_version = ">= 1.6.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66"
    }
  }
}

locals {
  proxmox_api_token = (
    var.proxmox_token_id != null && var.proxmox_token_secret != null
    ? "${var.proxmox_token_id}=${var.proxmox_token_secret}"
    : null
  )
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = local.proxmox_api_token
  insecure  = var.proxmox_insecure

  ssh {
    agent    = true
    username = var.proxmox_ssh_username

    dynamic "node" {
      for_each = var.proxmox_node_addresses
      content {
        name    = node.key
        address = node.value
      }
    }
  }
}
""",
    "infra/terraform/modules/vm/variables.tf": """variable "name" { type = string }
variable "node_name" { type = string }
variable "vm_id" { type = number }
variable "cpu_cores" {
  type    = number
  default = 2
  validation {
    condition     = var.cpu_cores >= 1 && var.cpu_cores <= 64
    error_message = "cpu_cores must be between 1 and 64."
  }
}
variable "memory_mb" {
  type    = number
  default = 4096
  validation {
    condition     = var.memory_mb >= 512
    error_message = "memory_mb must be at least 512MB."
  }
}
variable "disk_gb" {
  type    = number
  default = 32
  validation {
    condition     = var.disk_gb >= 8
    error_message = "disk_gb must be at least 8GB."
  }
}
variable "bridge" {
  type    = string
  default = "vmbr0"
  validation {
    condition     = can(regex("^vmbr[0-9]+$", var.bridge))
    error_message = "bridge must be in vmbrN format, for example vmbr0."
  }
}
variable "template_id" { type = number }
variable "datastore_id" {
  type    = string
  default = "local-lvm"
}
variable "started" {
  type    = bool
  default = true
}
variable "tags" {
  type    = list(string)
  default = []
}
""",
    "infra/terraform/modules/vm/main.tf": """terraform {
  required_providers {
    proxmox = {
      source = "bpg/proxmox"
    }
  }
}

resource "proxmox_virtual_environment_vm" "this" {
  name      = var.name
  node_name = var.node_name
  vm_id     = var.vm_id
  started   = var.started
  tags      = var.tags

  cpu {
    cores = var.cpu_cores
  }

  memory {
    dedicated = var.memory_mb
  }

  network_device {
    bridge = var.bridge
  }

  disk {
    interface    = "scsi0"
    datastore_id = var.datastore_id
    size         = var.disk_gb
  }

  clone {
    vm_id = var.template_id
    full  = true
  }

  initialization {
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
  }
}
""",
    "infra/terraform/modules/vm/outputs.tf": """output "name" { value = proxmox_virtual_environment_vm.this.name }
output "vm_id" { value = proxmox_virtual_environment_vm.this.vm_id }
""",
    "infra/terraform/modules/lxc-debian/variables.tf": """variable "name" { type = string }
variable "node_name" { type = string }
variable "vm_id" { type = number }
variable "cores" {
  type    = number
  default = 2
  validation {
    condition     = var.cores >= 1 && var.cores <= 32
    error_message = "cores must be between 1 and 32."
  }
}
variable "memory_mb" {
  type    = number
  default = 2048
  validation {
    condition     = var.memory_mb >= 256
    error_message = "memory_mb must be at least 256MB."
  }
}
variable "disk_gb" {
  type    = number
  default = 16
  validation {
    condition     = var.disk_gb >= 4
    error_message = "disk_gb must be at least 4GB."
  }
}
variable "bridge" {
  type    = string
  default = "vmbr0"
  validation {
    condition     = can(regex("^vmbr[0-9]+$", var.bridge))
    error_message = "bridge must be in vmbrN format, for example vmbr0."
  }
}
variable "template_file_id" { type = string }
variable "datastore_id" {
  type    = string
  default = "local-lvm"
}
variable "started" {
  type    = bool
  default = true
}
""",
    "infra/terraform/modules/lxc-debian/main.tf": """terraform {
  required_providers {
    proxmox = {
      source = "bpg/proxmox"
    }
  }
}

resource "proxmox_virtual_environment_container" "this" {
  node_name = var.node_name
  vm_id     = var.vm_id
  unprivileged = true
  started   = var.started

  initialization {
    hostname = var.name
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
  }

  network_interface {
    name   = "eth0"
    bridge = var.bridge
  }

  disk {
    datastore_id = var.datastore_id
    size         = var.disk_gb
  }

  operating_system {
    template_file_id = var.template_file_id
    type             = "debian"
  }

  cpu {
    cores = var.cores
  }

  memory {
    dedicated = var.memory_mb
  }
}
""",
    "infra/terraform/modules/lxc-debian/outputs.tf": """output "name" { value = proxmox_virtual_environment_container.this.initialization[0].hostname }
output "vm_id" { value = proxmox_virtual_environment_container.this.vm_id }
""",
    "infra/terraform/environments/homelab/variables.tf": """variable "proxmox_endpoint" { type = string }
variable "proxmox_token_id" {
  type        = string
  sensitive   = true
  description = "Proxmox API token ID (for example terraform@pve!proxmox-compose)."
}
variable "proxmox_token_secret" {
  type      = string
  sensitive = true
}
variable "proxmox_insecure" {
  type    = bool
  default = true
}
variable "proxmox_ssh_username" {
  type        = string
  default     = "root"
  description = "SSH username for provider node connections."
}
variable "proxmox_node_addresses" {
  type        = map(string)
  default     = {}
  description = "Optional mapping of Proxmox node names to SSH-resolvable addresses."
}

variable "allowed_nodes" {
  type        = list(string)
  default     = []
  description = "Optional allowlist of Proxmox node names."
}

variable "default_vm_datastore_id" {
  type    = string
  default = "local-lvm"
}

variable "default_lxc_datastore_id" {
  type    = string
  default = "local-lvm"
}

variable "vms" {
  type = list(object({
    name        = string
    node_name   = string
    vm_id       = number
    template_id = number
    os          = optional(string, "debian")
    ansible_host = optional(string)
    ansible_user = optional(string)
    cpu_cores   = optional(number, 2)
    memory_mb   = optional(number, 4096)
    disk_gb     = optional(number, 32)
    bridge      = optional(string, "vmbr0")
    datastore_id = optional(string)
    started      = optional(bool, true)
    tags         = optional(list(string), [])
  }))
  default = []
  validation {
    condition     = length(distinct([for vm in var.vms : vm.name])) == length(var.vms)
    error_message = "Each VM name must be unique."
  }
  validation {
    condition     = length(distinct([for vm in var.vms : vm.vm_id])) == length(var.vms)
    error_message = "Each VM vm_id must be unique."
  }
  validation {
    condition = alltrue([
      for vm in var.vms : contains(["debian", "fedora"], lower(vm.os))
    ])
    error_message = "VM os must be either debian or fedora."
  }
  validation {
    condition = length(var.allowed_nodes) == 0 || alltrue([
      for vm in var.vms : contains(var.allowed_nodes, vm.node_name)
    ])
    error_message = "VM node_name must exist in allowed_nodes."
  }
}

variable "debian_lxcs" {
  type = list(object({
    name             = string
    node_name        = string
    vm_id            = number
    template_file_id = string
    ansible_host     = optional(string)
    ansible_user     = optional(string)
    cores            = optional(number, 2)
    memory_mb        = optional(number, 2048)
    disk_gb          = optional(number, 16)
    bridge           = optional(string, "vmbr0")
    datastore_id     = optional(string)
    started          = optional(bool, true)
  }))
  default = []
  validation {
    condition     = length(distinct([for lxc in var.debian_lxcs : lxc.name])) == length(var.debian_lxcs)
    error_message = "Each Debian LXC name must be unique."
  }
  validation {
    condition     = length(distinct([for lxc in var.debian_lxcs : lxc.vm_id])) == length(var.debian_lxcs)
    error_message = "Each Debian LXC vm_id must be unique."
  }
  validation {
    condition = alltrue([
      for lxc in var.debian_lxcs : can(regex("debian", lower(lxc.template_file_id)))
    ])
    error_message = "Debian LXC template_file_id must clearly reference a Debian template."
  }
  validation {
    condition = length(var.allowed_nodes) == 0 || alltrue([
      for lxc in var.debian_lxcs : contains(var.allowed_nodes, lxc.node_name)
    ])
    error_message = "LXC node_name must exist in allowed_nodes."
  }
}
""",
    "infra/terraform/environments/homelab/main.tf": """module "vms" {
  for_each = { for vm in var.vms : vm.name => vm }
  source   = "../../modules/vm"

  name        = each.value.name
  node_name   = each.value.node_name
  vm_id       = each.value.vm_id
  template_id = each.value.template_id
  cpu_cores   = each.value.cpu_cores
  memory_mb   = each.value.memory_mb
  disk_gb     = each.value.disk_gb
  bridge      = each.value.bridge
  datastore_id = try(each.value.datastore_id, var.default_vm_datastore_id)
  started      = each.value.started
  tags         = each.value.tags
}

module "debian_lxcs" {
  for_each = { for lxc in var.debian_lxcs : lxc.name => lxc }
  source   = "../../modules/lxc-debian"

  name             = each.value.name
  node_name        = each.value.node_name
  vm_id            = each.value.vm_id
  template_file_id = each.value.template_file_id
  cores            = each.value.cores
  memory_mb        = each.value.memory_mb
  disk_gb          = each.value.disk_gb
  bridge           = each.value.bridge
  datastore_id     = try(each.value.datastore_id, var.default_lxc_datastore_id)
  started          = each.value.started
}

output "vms" {
  value = {
    for vm in var.vms : vm.name => {
      name         = vm.name
      vm_id        = vm.vm_id
      os           = vm.os
      ansible_host = try(vm.ansible_host, vm.name)
      ansible_user = try(vm.ansible_user, "debian")
    }
  }
}

output "debian_lxcs" {
  value = {
    for lxc in var.debian_lxcs : lxc.name => {
      name         = lxc.name
      vm_id        = lxc.vm_id
      ansible_host = try(lxc.ansible_host, lxc.name)
      ansible_user = try(lxc.ansible_user, "root")
    }
  }
}
""",
    "infra/terraform/environments/homelab/terraform.tfvars.example": """proxmox_endpoint = "https://proxmox.local:8006/api2/json"
proxmox_token_id     = "terraform@pve!proxmox-compose"
proxmox_token_secret = "change-me"
proxmox_insecure = true
proxmox_ssh_username = "root"
# Optional node name -> IP/FQDN mapping to avoid DNS issues for node names
proxmox_node_addresses = {
  pve1 = "192.168.50.15"
}
allowed_nodes    = ["pve1", "pve2"]
default_vm_datastore_id  = "local-lvm"
default_lxc_datastore_id = "local-lvm"

vms = [
  {
    name         = "frigate-vm"
    node_name    = "pve1"
    vm_id        = 201
    template_id  = 9001
    os           = "debian"
    ansible_host = "frigate-vm.local"
    ansible_user = "debian"
    cpu_cores    = 4
    memory_mb    = 8192
    disk_gb      = 64
    bridge       = "vmbr0"
    datastore_id = "local-lvm"
    started      = true
    tags         = ["homelab", "vm", "frigate"]
  },
]

debian_lxcs = [
  {
    name             = "postgres-lxc"
    node_name        = "pve1"
    vm_id            = 301
    template_file_id = "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
    ansible_host     = "postgres-lxc.local"
    ansible_user     = "root"
    cores            = 2
    memory_mb        = 2048
    disk_gb          = 24
    bridge           = "vmbr0"
    datastore_id     = "local-lvm"
    started          = true
  },
]
""",
    "config/ansible/ansible.cfg": """[defaults]
inventory = ./inventory/hosts.yml
roles_path = ./roles
host_key_checking = False
stdout_callback = ansible.builtin.default
result_format = yaml
""",
    "config/ansible/inventory/static.yml": """all:
  children:
    debian_vms:
      hosts: {}
    fedora_vms:
      hosts: {}
    debian_lxcs:
      hosts: {}
    existing_hosts:
      hosts: {}
    existing_docker_vms:
      hosts: {}
""",
    "config/ansible/inventory/generated.yml": """all:
  children: {}
""",
    "config/ansible/group_vars/all/main.yml": """ansible_python_interpreter: /usr/bin/python3

vm_compose_apps:
  - repo: "https://github.com/example/frigate-stack.git"
    dest: "/opt/frigate"
    version: "main"
    compose: true

lxc_systemd_services: []
""",
    "config/ansible/group_vars/all/vault.example.yml": """# Encrypt this file as vault.yml using ansible-vault.
#
# example:
# private_repo_deploy_key: |
#   -----BEGIN OPENSSH PRIVATE KEY-----
#   ...
#   -----END OPENSSH PRIVATE KEY-----
#
# frigate_env_content: |
#   MQTT_PASSWORD=...
#   OPENAI_API_KEY=...
#   GEMINI_API_KEY=...
""",
    "config/ansible/host_vars/example_existing_docker_vm.yml": """# Example host_vars for an existing Docker VM.
# Rename this file to match your inventory host name, for example:
# config/ansible/host_vars/frigate_vm.yml

vm_compose_apps:
  - dest: "/opt/frigate"
    owner: "root"
    group: "root"
    compose: true
    compose_file_name: "docker-compose.yaml"
    compose_file_content: |
      services:
        frigate:
          image: ghcr.io/blakeblackshear/frigate:0.17.1
          restart: unless-stopped
    env_content: "{{ frigate_env_content }}"
""",
    "config/ansible/playbooks/post-provision.yml": """- name: Configure provisioned VMs and LXCs
  hosts: debian_vms:fedora_vms:debian_lxcs
  become: true
  roles:
    - role: common

- name: Configure Docker workloads on VMs
  hosts: debian_vms:fedora_vms
  become: true
  roles:
    - role: vm_docker

- name: Configure systemd services on Debian LXCs
  hosts: debian_lxcs
  become: true
  roles:
    - role: lxc_systemd_service
""",
    "config/ansible/playbooks/provision-existing.yml": """- name: Converge existing infrastructure
  hosts: existing_hosts
  become: true
  roles:
    - role: common
    - role: existing_maintenance

- name: Converge Docker workloads on existing VMs
  hosts: existing_docker_vms
  become: true
  roles:
    - role: vm_docker
""",
    "config/ansible/roles/common/tasks/main.yml": """- name: Update apt packages
  ansible.builtin.apt:
    update_cache: true
    cache_valid_time: 3600
  when: ansible_os_family == "Debian"

- name: Install Debian baseline packages
  ansible.builtin.apt:
    name: "{{ common_packages_debian }}"
    state: present
  when: ansible_os_family == "Debian"

- name: Install Fedora baseline packages
  ansible.builtin.dnf:
    name: "{{ common_packages_fedora }}"
    state: present
  when: ansible_distribution == "Fedora"
""",
    "config/ansible/roles/common/defaults/main.yml": """common_packages_debian:
  - curl
  - git
  - htop
  - jq
  - python3

common_packages_fedora:
  - curl
  - git
  - htop
  - jq
  - python3
""",
    "config/ansible/roles/vm_docker/tasks/main.yml": """- name: Install Docker on Debian
  ansible.builtin.apt:
    name:
      - docker.io
      - docker-compose-plugin
    state: present
  when: ansible_os_family == "Debian"

- name: Install Docker on Fedora
  ansible.builtin.dnf:
    name:
      - docker
      - docker-compose
    state: present
  when: ansible_distribution == "Fedora"

- name: Ensure docker service enabled
  ansible.builtin.service:
    name: docker
    enabled: true
    state: started

- name: Deploy compose applications
  ansible.builtin.include_role:
    name: deploy_git_app
  vars:
    deploy_git_apps: "{{ vm_compose_apps }}"
""",
    "config/ansible/roles/vm_docker/defaults/main.yml": """vm_compose_apps: []
""",
    "config/ansible/roles/deploy_git_app/tasks/main.yml": """- name: Ensure app directories exist
  ansible.builtin.file:
    path: "{{ item.dest }}"
    state: directory
    owner: "{{ item.owner | default('root') }}"
    group: "{{ item.group | default('root') }}"
    mode: "0755"
  loop: "{{ deploy_git_apps }}"

- name: Checkout repositories
  ansible.builtin.git:
    repo: "{{ item.repo }}"
    dest: "{{ item.dest }}"
    version: "{{ item.version | default('main') }}"
    key_file: "{{ item.key_file | default(omit) }}"
    accept_hostkey: true
  loop: "{{ deploy_git_apps }}"

- name: Deploy compose stacks
  community.docker.docker_compose_v2:
    project_src: "{{ item.dest }}"
    state: present
  when: item.compose | default(true)
  loop: "{{ deploy_git_apps }}"
""",
    "config/ansible/roles/deploy_git_app/defaults/main.yml": """deploy_git_apps: []
""",
    "config/ansible/roles/lxc_systemd_service/tasks/main.yml": """- name: Install Debian packages for LXC services
  ansible.builtin.apt:
    update_cache: true
    name: "{{ lxc_packages }}"
    state: present

- name: Deploy app repositories for service workloads
  ansible.builtin.include_role:
    name: deploy_git_app
  vars:
    deploy_git_apps: "{{ lxc_git_apps }}"

- name: Install systemd unit files
  ansible.builtin.template:
    src: service.j2
    dest: "/etc/systemd/system/{{ item.name }}.service"
    mode: "0644"
  loop: "{{ lxc_systemd_services }}"
  notify: Restart LXC services

- name: Enable and start services
  ansible.builtin.service:
    name: "{{ item.name }}"
    enabled: true
    state: started
  loop: "{{ lxc_systemd_services }}"
""",
    "config/ansible/roles/lxc_systemd_service/defaults/main.yml": """lxc_packages:
  - postgresql
  - redis-server

lxc_git_apps: []

lxc_systemd_services: []
""",
    "config/ansible/roles/lxc_systemd_service/handlers/main.yml": """- name: Restart LXC services
  ansible.builtin.systemd:
    daemon_reload: true
    name: "{{ item.name }}"
    state: restarted
  loop: "{{ lxc_systemd_services }}"
""",
    "config/ansible/roles/lxc_systemd_service/templates/service.j2": """[Unit]
Description={{ item.description | default(item.name) }}
After=network-online.target

[Service]
Type=simple
User={{ item.user | default('root') }}
WorkingDirectory={{ item.working_dir | default('/') }}
ExecStart={{ item.exec_start }}
Restart=always
RestartSec=5
Environment={{ item.environment | default('') }}

[Install]
WantedBy=multi-user.target
""",
    "config/ansible/roles/existing_maintenance/tasks/main.yml": """- name: Run host update script if configured
  ansible.builtin.shell: "{{ existing_update_script }}"
  args:
    executable: /bin/bash
  when: existing_update_script | length > 0

- name: Install lm-sensors on Debian/Fedora
  ansible.builtin.package:
    name: lm_sensors
    state: present
""",
    "config/ansible/roles/existing_maintenance/defaults/main.yml": """existing_update_script: ""
""",
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
2. Define host vars in `config/ansible/host_vars/<host>.yml` with compose content or repo source.
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
    "docs/service-onboarding.md": """# VM Service Onboarding

Use this flow for VM docker-compose apps (for example Frigate):
1. Add VM definition in Terraform vars.
2. Add host to `debian_vms` or `fedora_vms` inventory grouping.
3. Set `vm_compose_apps` host/group vars with repo and destination.
4. Re-run `proxmox-compose apply`.
""",
    "docs/lxc-service-onboarding.md": """# Debian LXC Service Onboarding

Use this flow for Debian LXC systemd workloads:
1. Add LXC in Terraform vars (`debian_lxcs`).
2. Define `lxc_packages` and `lxc_git_apps` as needed.
3. Define `lxc_systemd_services` entries with `exec_start`.
4. Re-run `proxmox-compose apply`.
""",
    "docs/secrets-and-ci.md": """# Secrets and CI

## Secrets
- Keep sensitive values out of `terraform.tfvars`.
- Use `~/.config/proxmox-compose/profiles.yml` for local profile env vars.
- Use Ansible Vault for repository secrets (`group_vars/all/vault.yml`).

## CI Validation
Run these checks in CI:
1. `terraform fmt -check`
2. `terraform validate`
3. `ansible-playbook --syntax-check`
""",
    ".github/workflows/validate.yml": """name: validate

on:
  pull_request:
  push:
    branches: [main]

jobs:
  iac-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: hashicorp/setup-terraform@v3
      - name: Install CLI test dependencies
        run: pip install pytest typer PyYAML
      - name: Run CLI tests
        run: PYTHONPATH=cli/src python -m pytest cli/tests -q
      - name: Terraform fmt
        run: terraform fmt -check -recursive infra/terraform
      - name: Terraform init and validate
        run: |
          cd infra/terraform/environments/homelab
          terraform init -backend=false
          terraform validate
      - name: Ansible syntax check
        run: |
          pipx install ansible
          cd config/ansible
          ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
""",
}

