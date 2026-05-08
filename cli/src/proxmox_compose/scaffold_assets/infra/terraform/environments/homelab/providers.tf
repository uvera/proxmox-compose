terraform {
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
  insecure  = var.proxmox_insecure
  api_token = var.proxmox_auth_method == "api_token" ? "${var.proxmox_token_id}=${var.proxmox_token_secret}" : null
  username  = var.proxmox_auth_method == "password" ? var.proxmox_username : null
  password  = var.proxmox_auth_method == "password" ? var.proxmox_password : null

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
