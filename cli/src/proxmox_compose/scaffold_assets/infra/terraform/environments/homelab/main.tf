module "vms" {
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
  ssh_public_keys = length(try(each.value.ssh_public_keys, [])) > 0 ? each.value.ssh_public_keys : (
    var.default_lxc_ssh_public_key_path != null ? [trimspace(file(pathexpand(var.default_lxc_ssh_public_key_path)))] : []
  )
  ipv4_cidr    = try(each.value.ipv4_cidr, null)
  ipv4_gateway = try(each.value.ipv4_gateway, null)
  cores        = each.value.cores
  memory_mb    = each.value.memory_mb
  disk_gb      = each.value.disk_gb
  bridge       = each.value.bridge
  datastore_id = try(each.value.datastore_id, var.default_lxc_datastore_id)
  started      = each.value.started
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
