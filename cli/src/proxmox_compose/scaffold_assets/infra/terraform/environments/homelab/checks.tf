check "proxmox_api_credentials" {
  assert {
    condition = (
      var.proxmox_auth_method == "api_token" ? (
        coalesce(var.proxmox_token_id, "") != "" && coalesce(var.proxmox_token_secret, "") != ""
        ) : (
        coalesce(var.proxmox_username, "") != "" && coalesce(var.proxmox_password, "") != ""
      )
    )
    error_message = "When proxmox_auth_method is api_token, set proxmox_token_id and proxmox_token_secret. When password, set proxmox_username and proxmox_password."
  }
}
