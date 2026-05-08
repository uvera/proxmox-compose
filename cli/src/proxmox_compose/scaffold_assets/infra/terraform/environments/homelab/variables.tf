variable "proxmox_endpoint" { type = string }

variable "proxmox_token_id" {
  type        = string
  sensitive   = true
  description = "Proxmox API token ID (for example terraform@pve!proxmox-compose)."
}

variable "proxmox_token_secret" {
  type        = string
  sensitive   = true
  description = "Proxmox API token secret paired with proxmox_token_id."
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

variable "default_lxc_ssh_public_key_path" {
  type        = string
  default     = null
  description = "Optional local path to SSH public key injected into Debian LXCs when per-LXC ssh_public_keys is not set."
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
    name              = string
    node_name         = string
    vm_id             = number
    template_file_id  = string
    ansible_host      = optional(string)
    ansible_user      = optional(string)
    ssh_public_keys   = optional(list(string), [])
    ipv4_cidr         = optional(string)
    ipv4_gateway      = optional(string)
    cores             = optional(number, 2)
    memory_mb         = optional(number, 2048)
    disk_gb           = optional(number, 16)
    bridge            = optional(string, "vmbr0")
    datastore_id      = optional(string)
    started           = optional(bool, true)
    lxc_features_fuse = optional(bool, false)
    # Rare; enable only if a workload requires keyctl inside the CT.
    lxc_features_keyctl = optional(bool, false)
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
