"""リモートからの指示を受けて動作するフロント側コントローラー。"""

from __future__ import annotations

import contextlib
import threading
from typing import TYPE_CHECKING

from src.front.communication_server import CommunicationServer
from src.front.meet_participant import MeetParticipant
from src.models.enums import MessageType, RemoteCommand
from src.models.state import AppStatus, NetworkCondition, StatusMessage
from src.utils.network_utils import diagnose_network

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.utils.notification_service import FrontNotifier


class FrontController:
    """Coordinates the passive front-side workflow."""

    def __init__(
        self,
        notifier: FrontNotifier,
        host: str = "0.0.0.0",  # noqa: S104
        port: int = 9999,
        display_name: str = "Reception",
    ) -> None:
        self._notifier = notifier
        self._host = host
        self._port = port
        self._display_name = display_name

        self._status_callback: Callable[[StatusMessage], None] | None = None
        self._network_callback: Callable[[str], None] | None = None
        self._error_callback: Callable[[str], None] | None = None

        self._server = CommunicationServer(host=self._host, port=self._port)
        self._server.register_handler(MessageType.MEET_URL.value, self._handle_meet_url)
        self._server.register_handler(MessageType.COMMAND.value, self._handle_command)
        self._server.set_connection_callbacks(
            on_connected=self._on_client_connected,
            on_disconnected=self._on_client_disconnected,
        )

        self._participant: MeetParticipant | None = None
        self._current_meet_url: str | None = None
        self._current_remote_label: str | None = None
        self._server_running = False
        self._session_lock = threading.RLock()
        self._session_active = False

    # ------------------------------------------------------------------
    # コールバック登録
    # ------------------------------------------------------------------
    def attach_callbacks(
        self,
        status_callback: Callable[[StatusMessage], None],
        network_callback: Callable[[str], None],
        error_callback: Callable[[str], None],
    ) -> None:
        self._status_callback = status_callback
        self._network_callback = network_callback
        self._error_callback = error_callback

    # ------------------------------------------------------------------
    # UI更新用ヘルパー
    # ------------------------------------------------------------------
    def _emit_status(self, status: AppStatus, headline: str, detail: str | None = None) -> None:
        if self._status_callback:
            self._status_callback(StatusMessage(status=status, headline=headline, detail=detail))

    def _emit_network(self, message: str) -> None:
        if self._network_callback:
            self._network_callback(message)

    def _emit_error(self, message: str) -> None:
        if self._error_callback:
            self._error_callback(message)

    # ------------------------------------------------------------------
    # ライフサイクル処理
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        result = diagnose_network()
        self._emit_network(result.message)
        if result.condition == NetworkCondition.OK:
            self._emit_error("")
            self._ensure_server()
        else:
            self._emit_error(
                f"{result.message}\n\n"
                "以下をご確認ください：\n"
                "• Windows立ち上げ直後はTailscaleアプリが未起動の可能性があります。しばらくしてから接続先更新ボタンを押してみてください。\n"  # noqa: E501
                "• インターネット接続は正常ですか？\n\n"
                "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。",
            )
            self._emit_status(AppStatus.ERROR, "ネットワークを確認してください")

    def retry_network(self) -> None:
        result = diagnose_network()
        self._emit_network(result.message)
        if result.condition == NetworkCondition.OK:
            self._emit_error("")
            self._ensure_server()
        else:
            self._emit_error(
                f"{result.message}\n\n"
                "以下をご確認ください：\n"
                "• Tailscaleアプリは起動していますか？\n"
                "• インターネット接続は正常ですか？\n\n"
                "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。",
            )
            self._emit_status(AppStatus.ERROR, "ネットワークを確認してください")

    def shutdown(self) -> None:
        self._teardown_session()
        if self._server_running:
            self._server.stop_server()
            self._server_running = False

    # ------------------------------------------------------------------
    # サーバー管理
    # ------------------------------------------------------------------
    def _ensure_server(self) -> None:
        if self._server_running:
            if not self._session_active:
                self._emit_status(AppStatus.IDLE, "リモートPCからの接続を待機中")
            return
        success = self._server.start_server()
        if success:
            self._server_running = True
            self._emit_status(AppStatus.IDLE, "リモートPCからの接続を待機中")
        else:
            self._notifier.report_error(
                RuntimeError("server start failed"),
                "フロントサーバー起動",
                {"ホスト": self._host, "ポート": self._port},
            )
            self._emit_error(
                "サーバーを開始できませんでした。\n\n"
                "以下をご確認ください：\n"
                "• Tailscaleは正常に動作していますか？\n"
                "• 本システムを複数起動済みではありませんか？すべて閉じてから再度起動してください。\n"
                "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。",
            )
            self._emit_status(AppStatus.ERROR, "サーバーを開始できませんでした")

    # ------------------------------------------------------------------
    # CommunicationServer からの通知ハンドラー
    # ------------------------------------------------------------------
    def _on_client_connected(self, address: tuple) -> None:
        self._current_remote_label = f"{address[0]}"
        if not self._session_active:
            self._emit_status(AppStatus.CONNECTING, "リモートPCが接続しました", f"端末: {self._current_remote_label}")

    def _on_client_disconnected(self, _address: tuple) -> None:
        self._teardown_session()
        if self._server_running:
            self._emit_status(AppStatus.IDLE, "リモートPCからの接続を待機中")

    def _handle_meet_url(self, data: dict) -> None:
        meet_url = data.get("content")
        if not meet_url:
            self._notifier.report_error(
                RuntimeError("no meet url"),
                "Meet URL受信",
                {"メッセージ": data},
            )
            self._emit_error(
                "Meet URLを受信できませんでした。\n\nシステム管理者にお問い合わせください。",
            )
            return
        self._current_meet_url = meet_url
        self._emit_status(
            AppStatus.CONNECTING,
            "接続要求を受信しました",
            f"Meet URL: {meet_url}",
        )
        self._start_meeting(meet_url)

    def _handle_command(self, data: dict) -> None:
        command = data.get("content")
        if command == RemoteCommand.END_SESSION.value:
            self._emit_status(AppStatus.DISCONNECTING, "セッションを終了します")
            self._teardown_session()
            self._emit_status(AppStatus.IDLE, "リモートPCからの接続を待機中")

    # ------------------------------------------------------------------
    # Meet操作ヘルパー
    # ------------------------------------------------------------------
    def _start_meeting(self, meet_url: str) -> None:
        with self._session_lock:
            self._session_active = True
        try:
            if self._participant:
                self._participant.cleanup()
            self._participant = MeetParticipant(display_name=self._display_name)
            if not self._participant.join_meeting(meet_url):
                msg = (
                    "Google Meetへの参加に失敗しました。\n\n"
                    "以下をご確認ください：\n"
                    "• ブラウザの権限設定でカメラ・マイクは許可されていますか？\n"
                    "• インターネット接続は安定していますか？\n"
                    "上記を確認しても解決しない場合は、システム管理者にお問い合わせください。"
                )
                raise RuntimeError(msg)  # noqa: TRY301
            detail = "現在対応中です"
            if self._current_remote_label:
                detail = f"接続端末: {self._current_remote_label}"
            self._emit_status(AppStatus.CONNECTED, "接続中", detail)
            # 入室完了をSlack通知
            if self._current_remote_label and meet_url:
                self._notifier.room_entry_complete(meet_url)
        except Exception as exc:  # noqa: BLE001
            self._notifier.report_error(exc, "フロントMeet参加", {"Meet URL": meet_url})
            self._emit_status(AppStatus.ERROR, "Meetへの参加に失敗しました")
            self._emit_error(str(exc))
            self._teardown_session()
        else:
            self._emit_error("")

    def _teardown_session(self) -> None:
        with self._session_lock:
            if not self._session_active:
                return
            self._session_active = False
        if self._participant:
            with contextlib.suppress(Exception):
                self._participant.leave_meeting()
            with contextlib.suppress(Exception):
                self._participant.cleanup()
        self._participant = None
        self._current_meet_url = None
        self._current_remote_label = None
