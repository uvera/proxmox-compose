TERRAFORM_SCAFFOLD_FILES: dict[str, str] = {
    "infra/terraform/environments/homelab/providers.tf": """terraform {
  required_version = ">= 1.6.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = "${var.proxmox_token_id}=${var.proxmox_token_secret}"
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
variable "ipv4_cidr" {
  type        = string
  default     = null
  description = "Optional static IPv4 CIDR (for example 192.168.50.42/24). Uses DHCP when null."
}
variable "ipv4_gateway" {
  type        = string
  default     = null
  description = "Optional IPv4 gateway for static addressing."
}
variable "ssh_public_keys" {
  type        = list(string)
  default     = []
  description = "Optional SSH public keys to inject for the default container user."
}
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
        address = coalesce(var.ipv4_cidr, "dhcp")
        gateway = var.ipv4_gateway
      }
    }
    user_account {
      keys = var.ssh_public_keys
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
    name         = string
    node_name    = string
    vm_id        = number
    template_id  = number
    os           = optional(string, "debian")
    ansible_host = optional(string)
    ansible_user = optional(string)
    cpu_cores    = optional(number, 2)
    memory_mb    = optional(number, 4096)
    disk_gb      = optional(number, 32)
    bridge       = optional(string, "vmbr0")
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
    ssh_public_keys  = optional(list(string), [])
    ipv4_cidr        = optional(string)
    ipv4_gateway     = optional(string)
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
    condition = alltrue([
      for lxc in var.debian_lxcs : (
        try(lxc.ipv4_gateway, null) == null || try(lxc.ipv4_cidr, null) != null
      )
    ])
    error_message = "When ipv4_gateway is set for an LXC, ipv4_cidr must also be set."
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

  name         = each.value.name
  node_name    = each.value.node_name
  vm_id        = each.value.vm_id
  template_id  = each.value.template_id
  cpu_cores    = each.value.cpu_cores
  memory_mb    = each.value.memory_mb
  disk_gb      = each.value.disk_gb
  bridge       = each.value.bridge
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
  ssh_public_keys  = try(each.value.ssh_public_keys, [])
  ipv4_cidr        = try(each.value.ipv4_cidr, null)
  ipv4_gateway     = try(each.value.ipv4_gateway, null)
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
      ansible_host = try(lxc.ansible_host, split("/", lxc.ipv4_cidr)[0], lxc.name)
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
    # Option A (DHCP + DNS): set ansible_host to a resolvable name/FQDN
    ansible_host     = "postgres-lxc.local"
    # Option B (static via Proxmox init): uncomment ipv4_* and either omit ansible_host
    # or set it to the same static IP.
    # ipv4_cidr      = "192.168.50.31/24"
    # ipv4_gateway   = "192.168.50.1"
    # Optional SSH public key injection for root/default user:
    # ssh_public_keys = [trimspace(file(pathexpand("~/.ssh/id_ed25519.pub")))]
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
}

