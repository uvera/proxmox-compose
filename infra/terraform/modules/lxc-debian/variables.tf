variable "name" { type = string }
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
