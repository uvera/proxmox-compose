variable "name" { type = string }
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
