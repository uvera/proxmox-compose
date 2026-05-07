terraform {
  required_providers {
    proxmox = {
      source = "bpg/proxmox"
    }
  }
}

resource "proxmox_virtual_environment_container" "this" {
  node_name    = var.node_name
  vm_id        = var.vm_id
  unprivileged = true
  started      = var.started
  features {
    nesting = true
    fuse    = var.features_fuse
    keyctl  = var.features_keyctl
  }

  # Existing LXCs may have feature flags that non-root API tokens are not
  # allowed to modify. Keep nesting for create while avoiding forbidden
  # feature reconciliation on already-managed containers.
  lifecycle {
    ignore_changes = [features]
  }

  # AppArmor / runc (CVE-2025-52881): the Terraform provider does not expose
  # lxc.apparmor.profile. Apply host-side CT config on the Proxmox node if Docker
  # fails inside the guest — see docs/lxc-docker-compose.md.

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
