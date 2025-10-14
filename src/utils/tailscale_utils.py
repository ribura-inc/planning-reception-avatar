"""Tailscale関連ユーティリティ.

Tailscaleの設定確認とIPアドレス取得
"""

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class TailscaleUtils:
    """Tailscale関連の操作を管理するユーティリティクラス"""

    @staticmethod
    def _get_tailscale_command() -> str:
        """適切なTailscaleコマンドパスを取得"""
        # macOSの場合、アプリケーション内のバイナリを確認
        tailscale_app_path = Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
        if tailscale_app_path.exists():
            return str(tailscale_app_path)
        # 他の環境では通常のコマンドを使用
        return "tailscale"

    @staticmethod
    def _get_status_data() -> dict | None:
        """Tailscaleステータスを取得"""
        try:
            tailscale_cmd = TailscaleUtils._get_tailscale_command()
            result = subprocess.run(  # noqa: S603
                [tailscale_cmd, "status", "--json"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(f"Tailscale status failed: {result.stderr}")
                return None

            return json.loads(result.stdout)

        except Exception:
            logger.exception("Error getting Tailscale status")
            return None

    @staticmethod
    def get_status_snapshot() -> dict | None:
        """Public helper to retrieve the raw status payload."""
        return TailscaleUtils._get_status_data()

    @staticmethod
    def check_tailscale_status() -> bool:
        """Tailscaleが正常に動作しているかを確認"""
        try:
            status = TailscaleUtils._get_status_data()
            if not status:
                return False

            # ログイン状態とバックエンドの確認
            backend_state = status.get("BackendState", "")
            if backend_state != "Running":
                logger.error(f"Tailscale is not running. State: {backend_state}")
                return False

            # 自分のデバイス情報を確認
            self_info = status.get("Self", {})
            if not self_info:
                logger.error("Self device information not found")
                return False

            logger.info(
                f"Tailscale is running. Device: {self_info.get('HostName', 'unknown')}",
            )
            return True  # noqa: TRY300
        except Exception:
            logger.exception("Unexpected error checking Tailscale status")
            return False

    @staticmethod
    def get_my_tailscale_ip() -> str | None:
        """自分のTailscale IPアドレスを取得"""
        try:
            tailscale_cmd = TailscaleUtils._get_tailscale_command()
            result = subprocess.run(  # noqa: S603
                [tailscale_cmd, "ip", "-4"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                ip = result.stdout.strip()
                logger.info(f"My Tailscale IP: {ip}")
            else:
                logger.error(f"Failed to get Tailscale IP: {result.stderr}")
                return None
            return ip  # noqa: TRY300
        except Exception:
            logger.exception("Error getting Tailscale IP")
            return None

    @staticmethod
    def get_tailscale_devices() -> dict[str, str]:
        """Tailscaleネットワーク内のデバイス一覧を取得"""
        try:
            status = TailscaleUtils._get_status_data()
            if not status:
                return {}

            devices = {}

            # ピアデバイスの情報を取得
            for peer in status.get("Peer", {}).values():
                hostname = peer.get("HostName", "")
                tailscale_ips = peer.get("TailscaleIPs", [])
                if hostname and tailscale_ips:
                    devices[hostname] = tailscale_ips[0]  # 最初のIPを使用

            # 自分のデバイス情報も追加
            self_info = status.get("Self", {})
            if self_info:
                hostname = self_info.get("HostName", "")
                tailscale_ips = self_info.get("TailscaleIPs", [])
                if hostname and tailscale_ips:
                    devices[hostname] = tailscale_ips[0]

            logger.info(f"Found {len(devices)} Tailscale devices")
        except Exception:
            logger.exception("Error getting Tailscale devices")
            return {}
        else:
            return devices

    @staticmethod
    def resolve_device_name(device_name: str) -> str | None:
        """デバイス名からTailscale IPアドレスを解決"""
        devices = TailscaleUtils.get_tailscale_devices()

        # 完全一致
        if device_name in devices:
            return devices[device_name]

        # 部分一致
        for hostname, ip in devices.items():
            if device_name.lower() in hostname.lower():
                logger.info(f"Resolved '{device_name}' to {hostname} ({ip})")
                return ip

        logger.error(f"Device '{device_name}' not found in Tailscale network")
        return None

    @staticmethod
    def check_and_setup_tailscale(  # noqa: PLR0911
        required_device: str | None = None,
    ) -> tuple[bool, str]:
        """Tailscaleの設定を確認し、必要に応じてエラーメッセージを返す

        Args:
            required_device: 必要なデバイス名（省略可能）

        Returns:
            (success, message): 成功フラグとメッセージ
        """
        try:
            # 1. Tailscaleコマンドの存在確認
            tailscale_cmd = TailscaleUtils._get_tailscale_command()

            try:
                subprocess.run(  # noqa: S603
                    [tailscale_cmd, "--version"],
                    check=False,
                    capture_output=True,
                    timeout=3,
                )
            except FileNotFoundError:
                return False, "Tailscaleがインストールされていません"

            # 2. ステータス確認
            if not TailscaleUtils.check_tailscale_status():
                return (
                    False,
                    "Tailscaleが正常に動作していません（ログインが必要な可能性があります）",
                )

            # 3. IPアドレス取得確認
            my_ip = TailscaleUtils.get_my_tailscale_ip()
            if not my_ip:
                return False, "Tailscale IPアドレスを取得できません"

            # 4. デバイス一覧取得確認
            devices = TailscaleUtils.get_tailscale_devices()
            if not devices:
                return False, "Tailscaleネットワーク内のデバイスが見つかりません"

            # 5. 特定のデバイスが必要な場合
            if required_device:
                ip = TailscaleUtils.resolve_device_name(required_device)
                if not ip:
                    device_list = ", ".join(devices.keys()) if devices else "なし"
                    return (
                        False,
                        f"デバイス '{required_device}' が見つかりません。利用可能なデバイス: {device_list}",
                    )

                return True, f"デバイス '{required_device}' を発見しました (IP: {ip})"

            return (
                True,
                f"Tailscaleセットアップ完了 (IP: {my_ip}, デバイス数: {len(devices)})",
            )

        except Exception:
            logger.exception("Tailscale検証中にエラーが発生しました")
            return False, "Tailscale検証中にエラーが発生しました"
