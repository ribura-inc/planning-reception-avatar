"""リモート側のUIとバックエンド処理を統括するコントローラー。"""

from __future__ import annotations

import contextlib
import threading
import time
from typing import TYPE_CHECKING

from src.models.enums import RemoteCommand
from src.models.state import AppStatus, StatusMessage
from src.remote.communication_client import CommunicationClient
from src.remote.meet_manager import MeetManager
from src.remote.webdriver_manager import cleanup_webdriver
from src.utils.network_utils import diagnose_network

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.utils.notification_service import RemoteNotifier


class RemoteController:
    """Encapsulates the remote-side orchestration logic."""

    def __init__(self, notifier: RemoteNotifier) -> None:
        self._notifier = notifier
        self._status_callback: Callable[[StatusMessage], None] | None = None
        self._network_callback = None
        self._devices_callback: Callable[[dict[str, str]], None] | None = None
        self._error_callback: Callable[[str], None] | None = None

        self._session_lock = threading.RLock()
        self._session_active = False
        self._current_device: str | None = None
        self._current_meet_url: str | None = None
        self._client: CommunicationClient | None = None
        self._meet_manager: MeetManager | None = None

    def attach_callbacks(
        self,
        status_callback: Callable[[StatusMessage], None],
        network_callback: Callable[[str], None],
        devices_callback: Callable[[dict[str, str]], None],
        error_callback: Callable[[str], None],
    ) -> None:
        self._status_callback = status_callback
        self._network_callback = network_callback
        self._devices_callback = devices_callback
        self._error_callback = error_callback

    # ------------------------------------------------------------
    # UI連携ヘルパー
    # ------------------------------------------------------------
    def _emit_status(self, status: AppStatus, headline: str, detail: str | None = None) -> None:
        if self._status_callback:
            self._status_callback(StatusMessage(status=status, headline=headline, detail=detail))

    def _emit_error(self, message: str) -> None:
        if self._error_callback:
            self._error_callback(message)

    def _emit_devices(self, devices: dict[str, str]) -> None:
        if self._devices_callback:
            self._devices_callback(devices)

    def _emit_network(self, message: str) -> None:
        if self._network_callback:
            self._network_callback(message)

    # ------------------------------------------------------------
    # ライフサイクル処理
    # ------------------------------------------------------------
    def initialize(self) -> None:
        """Initial network scan for device list."""
        result = diagnose_network()
        self._emit_network(result.message)
        self._emit_devices(result.tailscale_devices)
        if not result.tailscale_devices:
            self._emit_error("接続先が見つかりません。Tailscaleが起動しているか確認してください。")
        else:
            self._emit_error("")

    def refresh_devices(self) -> None:
        result = diagnose_network()
        self._emit_network(result.message)
        self._emit_devices(result.tailscale_devices)
        if not result.tailscale_devices:
            self._emit_error("接続先が見つかりません。Tailscaleが起動しているか確認してください。")
        else:
            self._emit_error("")

    # ------------------------------------------------------------
    # セッション制御
    # ------------------------------------------------------------
    def start_session(self, device_name: str) -> None:
        with self._session_lock:
            if self._session_active:
                self._emit_error("すでにセッションが開始されています")
                return
            self._session_active = True
            self._current_device = device_name

        try:
            self._emit_error("")
            self._emit_status(AppStatus.CONNECTING, "接続準備中", f"接続先: {device_name}")

            # デバイス名を解決しIPを取得（キャッシュ優先）
            self._emit_status(AppStatus.CONNECTING, "Meetを準備しています")
            meet_manager = MeetManager()
            meet_url = meet_manager.create_meet_space()
            self._current_meet_url = meet_url

            self._emit_status(AppStatus.CONNECTING, "フロントPCに接続しています")
            client = CommunicationClient(device_name, 9999)
            if not client.connect():
                msg = "フロントPCに接続できませんでした"
                raise RuntimeError(msg)  # noqa: TRY301

            self._emit_status(AppStatus.CONNECTING, "Meet URLを送信しています")
            if not client.send_meet_url(meet_url):
                msg = "Meet URLの送信に失敗しました"
                raise RuntimeError(msg)  # noqa: TRY301

            self._emit_status(AppStatus.CONNECTING, "ブラウザを準備しています")
            meet_manager.setup_browser()
            meet_manager.set_chrome_exit_callback(self._handle_chrome_exit)

            self._emit_status(AppStatus.CONNECTING, "Meetに参加しています")
            meet_manager.join_as_host(meet_url)
            time.sleep(1.5)
            meet_manager.enable_auto_admit()
            meet_manager.start_process_monitoring()

            self._client = client
            self._meet_manager = meet_manager

            self._emit_status(AppStatus.CONNECTED, "接続しました", f"Meet URL: {meet_url}")
            self._notifier.connection_ready(device_name, meet_url)

        except Exception as exc:  # noqa: BLE001
            self._notifier.report_error(exc, "リモート接続開始", {"接続先": device_name})
            self._emit_status(AppStatus.ERROR, "接続に失敗しました")
            self._emit_error(str(exc))
            cleanup_webdriver()
            self._teardown_session()
        else:
            self._emit_error("")

    def end_session(self) -> None:
        with self._session_lock:
            if not self._session_active:
                return

        try:
            self._emit_status(AppStatus.DISCONNECTING, "セッションを終了しています")
            if self._client:
                self._client.send_command(RemoteCommand.END_SESSION.value)
            self._notifier.disconnect_complete(self._current_device or "未指定")
        except Exception as exc:  # noqa: BLE001
            self._notifier.report_error(exc, "リモート切断", {"接続先": self._current_device})
            self._emit_error(str(exc))
        finally:
            self._teardown_session()
            self._emit_status(AppStatus.IDLE, "待機中")

    def shutdown(self) -> None:
        self._emit_status(AppStatus.SHUTTING_DOWN, "終了処理中")
        self._teardown_session()

    # ------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------
    def _handle_chrome_exit(self) -> None:
        self._emit_status(AppStatus.ERROR, "Chromeが終了しました")
        self._notifier.report_error(
            RuntimeError("Chrome terminated"),
            "Chrome監視",
            {"接続先": self._current_device, "Meet URL": self._current_meet_url},
        )
        self._teardown_session()

    def _teardown_session(self) -> None:
        with self._session_lock:
            if not self._session_active:
                return
            self._session_active = False

        if self._meet_manager:
            with contextlib.suppress(Exception):
                self._meet_manager.stop_process_monitoring()
        if self._meet_manager:
            cleanup_webdriver()

        if self._client:
            self._client.disconnect()

        self._client = None
        self._meet_manager = None
        self._current_meet_url = None
        self._current_device = None

        with self._session_lock:
            self._session_active = False
