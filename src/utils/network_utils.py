"""フロントとリモートで共通利用するネットワーク診断ロジック。"""

from __future__ import annotations

import socket
from contextlib import closing

from src.models.state import NetworkCheckResult, NetworkCondition

from .tailscale_utils import TailscaleUtils


def _has_internet_connectivity(timeout: float = 2.0) -> bool:
    """DNSソケットを用いた疎通確認でインターネット接続を判定する。"""
    try:
        with closing(socket.create_connection(("8.8.8.8", 53), timeout=timeout)):
            return True
    except OSError:
        return False


def diagnose_network() -> NetworkCheckResult:
    """Wi-FiとTailscaleの稼働状況を軽量に点検する。"""
    tailscale_status = TailscaleUtils.get_status_snapshot()

    tailscale_ok = False
    tailscale_devices: dict[str, str] = {}
    self_ip: str | None = None

    if tailscale_status:
        backend_state = tailscale_status.get("BackendState")
        tailscale_ok = backend_state == "Running"
        if tailscale_ok:
            self_info = tailscale_status.get("Self", {})
            tailscale_devices = TailscaleUtils.get_tailscale_devices()
            self_ip = (self_info.get("TailscaleIPs") or [None])[0]

    internet_ok = _has_internet_connectivity()

    if internet_ok and tailscale_ok:
        condition = NetworkCondition.OK
        message = "ネットワークは正常です"
    elif not internet_ok:
        condition = NetworkCondition.NO_INTERNET
        message = "インターネットに接続できません。Wi-Fiを確認してください。"
    elif not tailscale_ok:
        condition = NetworkCondition.TAILSCALE_UNAVAILABLE
        message = "Tailscaleが起動していません。アプリを起動してサインインしてください。"
    else:
        condition = NetworkCondition.UNKNOWN_ERROR
        message = "ネットワーク状態を判定できませんでした"

    return NetworkCheckResult(
        condition=condition,
        message=message,
        tailscale_devices=tailscale_devices,
        tailscale_self=self_ip,
    )
