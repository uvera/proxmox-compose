import os
from collections.abc import Callable
from getpass import getpass

PROXMOX_VE_OTP_ENV = "PROXMOX_VE_OTP"


def prompt_proxmox_otp(
    *,
    getpass_fn: Callable[[str], str] | None = None,
) -> None:
    """Prompt for TOTP and set PROXMOX_VE_OTP for the bpg/proxmox provider."""
    fn = getpass_fn if getpass_fn is not None else getpass
    if PROXMOX_VE_OTP_ENV in os.environ:
        del os.environ[PROXMOX_VE_OTP_ENV]
    code = fn("Proxmox OTP (TOTP): ").strip()
    if not code:
        raise RuntimeError("Proxmox OTP is required when using --prompt-proxmox-otp.")
    os.environ[PROXMOX_VE_OTP_ENV] = code
