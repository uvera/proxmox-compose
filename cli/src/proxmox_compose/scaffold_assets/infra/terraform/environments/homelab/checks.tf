check "proxmox_api_credentials" {
  assert {
    condition = (
      coalesce(var.proxmox_token_id, "") != "" && coalesce(var.proxmox_token_secret, "") != ""
    )
    error_message = "Set proxmox_token_id and proxmox_token_secret (via TF_VAR_* or terraform.tfvars)."
  }
}
