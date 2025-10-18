"""リモート側のUIとバックエンド処理を統括するコントローラー。"""

from __future__ import annotations

import contextlib
import threading
import time
from typing import TYPE_CHECKING

from src.config import Config
from src.models.enums import RemoteCommand
from src.models.state import AppStatus, StatusMessage
from src.remote.communication_client import CommunicationClient
from src.remote.meet_manager import MeetManager
from src.remote.webdriver_manager import cleanup_webdriver
from src.utils.network_utils import diagnose_network
from src.utils.vtube_studio_utils import check_and_setup_vtube_studio

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.utils.notification_service import RemoteNotifier


class RemoteController:
    """Encapsulates the remote-side orchestration logic."""

    _INITIAL_DEVICE_ERROR = (
        "接続先が見つかりません。\n\n"
        "以下をご確認ください：\n"
        "• Windows立ち上げ直後はTailscaleアプリが未起動の可能性があります。しばらくしてから接続先更新ボタンを押してみてください。\n"  # noqa: E501
        "• Tailscaleにログインしていますか？\n"
        "• フロントPCがTailscaleネットワークに接続されていますか？\n\n"
        "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。"
    )

    _REFRESH_DEVICE_ERROR = (
        "接続先が見つかりません。\n\n"
        "以下をご確認ください：\n"
        "• Tailscaleアプリは起動していますか？\n"
        "• Tailscaleにログインしていますか？\n"
        "• フロントPCがTailscaleネットワークに接続されていますか？\n\n"
        "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。"
    )

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
        self._refresh_devices_with_error(self._INITIAL_DEVICE_ERROR)

    def refresh_devices(self) -> None:
        self._refresh_devices_with_error(self._REFRESH_DEVICE_ERROR)

    # ------------------------------------------------------------
    # Precheck機能（Google login & 拡張機能チェック）
    # ------------------------------------------------------------
    def check_google_login(self) -> tuple[bool, str]:
        """Googleログイン状態をチェックし、結果を返す（headless実行、自動クリーンアップ）."""
        meet_manager = MeetManager()
        return meet_manager.check_google_login()

    def check_extension_installed(self) -> tuple[bool, str]:
        """拡張機能のインストール状態をチェックし、結果を返す（headless実行、自動クリーンアップ）."""
        meet_manager = MeetManager()
        return meet_manager.check_extension_installed()

    def open_google_login_page(self) -> None:
        """Googleログインページを開く."""
        meet_manager = MeetManager()
        meet_manager.open_google_login_page()

    def open_extension_page(self) -> None:
        """拡張機能ページを開く."""
        meet_manager = MeetManager()
        meet_manager.open_extension_page()

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

            self._emit_status(AppStatus.CHECKING, "VTube Studioを確認しています")
            vtube_ok, vtube_message = check_and_setup_vtube_studio()
            if not vtube_ok:
                msg = (
                    "VTube Studioの起動に失敗しました。\n\n"
                    "VTube Studioを手動で起動してから再度お試しください。\n"
                    f"詳細: {vtube_message}"
                )
                raise RuntimeError(msg)  # noqa: TRY301

            vtube_detail = "VTube Studioは既に起動しています"
            if isinstance(vtube_message, str) and vtube_message.lower().startswith(
                "vtube studio launched",
            ):
                vtube_detail = "VTube Studioを起動しました"

            self._emit_status(
                AppStatus.CONNECTING,
                "VTube Studioの準備が完了しました",
                vtube_detail,
            )

            self._emit_status(AppStatus.CONNECTING, "Meetを準備しています")
            meet_manager = MeetManager()
            meet_url = meet_manager.create_meet_space()
            self._current_meet_url = meet_url

            self._emit_status(AppStatus.CONNECTING, "フロントPCに接続しています")
            client = CommunicationClient(device_name, 9999)
            if not client.connect():
                msg = (
                    "フロントPCに接続できませんでした。\n\n"
                    "以下をご確認ください:\n"
                    "• フロントPCでシステムは起動済みですか?\n"
                    "• フロントPC画面に「ネットワーク正常」と表示されていますか?\n"
                    "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。"
                )
                raise RuntimeError(msg)  # noqa: TRY301

            self._emit_status(AppStatus.CONNECTING, "Meet URLを送信しています")
            if not client.send_meet_url(meet_url):
                msg = (
                    "Meet URLの送信に失敗しました。\n\n"
                    "以下をご確認ください:\n"
                    "• フロントPCとの通信が安定していますか?\n"
                    "• フロントPCでエラーが表示されていないか確認してください\n"
                    "• ネットワーク接続を確認してください\n\n"
                    "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。"
                )
                raise RuntimeError(msg)  # noqa: TRY301

            # 接続喪失時のコールバックを設定
            client.set_connection_lost_callback(self._handle_connection_lost)

            self._emit_status(AppStatus.CONNECTING, "ブラウザを準備しています")
            meet_manager.setup_browser()
            meet_manager.set_chrome_exit_callback(self._handle_chrome_exit)

            self._emit_status(AppStatus.CONNECTING, "Meetに参加しています")
            meet_manager.join_as_host(meet_url)
            time.sleep(Config.GoogleMeet.JOIN_COMPLETE_WAIT)
            meet_manager.enable_auto_admit()
            meet_manager.start_process_monitoring()

            self._client = client
            self._meet_manager = meet_manager

            self._emit_status(AppStatus.CONNECTED, "接続しました", f"Meet URL: {meet_url}")
            self._emit_error("")

        except Exception as exc:
            # エラーを報告してUI更新、その後クリーンアップして再raise
            self._notifier.report_error(exc, "リモート接続開始", {"接続先": device_name})
            self._emit_status(AppStatus.ERROR, "接続に失敗しました")
            self._emit_error(str(exc))
            cleanup_webdriver()
            self._teardown_session()
            # 想定外のエラーは上位に伝播（mainでキャッチされてSlack通知される）
            raise

    def end_session(self) -> None:
        with self._session_lock:
            if not self._session_active:
                return

        try:
            self._emit_status(AppStatus.DISCONNECTING, "セッションを終了しています")
            if self._client:
                self._client.send_command(RemoteCommand.END_SESSION.value)
            self._notifier.disconnect_complete(self._current_device or "未指定")
        finally:
            self._teardown_session()
            self._emit_status(AppStatus.IDLE, "待機中")

    def shutdown(self) -> None:
        self._teardown_session()

    # ------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------
    def _handle_chrome_exit(self) -> None:
        """Chrome終了時の処理（正常終了として扱う）"""
        self._emit_status(AppStatus.DISCONNECTING, "Chromeを終了しました")
        if self._current_device:
            self._notifier.disconnect_complete(self._current_device)
        self._teardown_session()
        self._emit_status(AppStatus.IDLE, "待機中")

    def _handle_connection_lost(self) -> None:
        """ハートビート失敗による接続喪失時の処理"""
        self._emit_status(AppStatus.ERROR, "フロントPCとの接続が切断されました")
        self._emit_error(
            "フロントPCとの接続が失われました。\n\n"
            "以下をご確認ください：\n"
            "• フロントPCのネットワーク接続は正常ですか？\n"
            "• フロントPCでシステムがまだ起動していますか？\n"
            "• フロントPCの画面にエラーが表示されていませんか？\n\n"
            "上記を確認後、再度接続してください。\n"
            "問題が解決しない場合は、システム管理者にお問い合わせください。",
        )
        # クリーンアップを実行
        self._teardown_session()
        self._emit_status(AppStatus.IDLE, "待機中")

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

    def _refresh_devices_with_error(self, message_when_empty: str) -> None:
        result = diagnose_network()
        self._emit_network(result.message)
        self._emit_devices(result.tailscale_devices)
        self._emit_error("" if result.tailscale_devices else message_when_empty)
