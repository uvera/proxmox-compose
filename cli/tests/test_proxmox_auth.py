import os

import pytest

from proxmox_compose.proxmox_auth import PROXMOX_VE_OTP_ENV, prompt_proxmox_otp


def test_prompt_proxmox_otp_sets_env_and_clears_stale(monkeypatch) -> None:
    monkeypatch.setenv(PROXMOX_VE_OTP_ENV, "stale")

    prompt_proxmox_otp(getpass_fn=lambda _prompt: " 123456 ")

    assert PROXMOX_VE_OTP_ENV in os.environ
    assert os.environ[PROXMOX_VE_OTP_ENV] == "123456"


def test_prompt_proxmox_otp_empty_raises(monkeypatch) -> None:
    monkeypatch.delenv(PROXMOX_VE_OTP_ENV, raising=False)

    with pytest.raises(RuntimeError, match="OTP is required"):
        prompt_proxmox_otp(getpass_fn=lambda _prompt: "   ")

    assert PROXMOX_VE_OTP_ENV not in os.environ
