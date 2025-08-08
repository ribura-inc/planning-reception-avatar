"""
受付ハンドラー（フロントPC用）
リモートPCからの指示を受けてMeet参加などを処理する
"""

import logging
import threading
import time
from typing import Any

from ..models.enums import ConnectionStatus, MessageType, RemoteCommand
from ..utils.slack import notify_error, notify_usage
from .communication_server import CommunicationServer
from .flet_gui import FrontGUI
from .meet_participant import MeetParticipant

logger = logging.getLogger(__name__)


class ReceptionHandler:
    """フロントPC用受付処理ハンドラー"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9999,
        display_name: str = "Reception",
        gui: FrontGUI | None = None,
    ):
        """
        Args:
            host: サーバーのホスト
            port: サーバーのポート
            display_name: Meet表示名
            gui: GUIオブジェクト（オプション）
        """
        self.host = host
        self.port = port
        self.display_name = display_name
        self.gui = gui

        # コンポーネント初期化
        self.server = CommunicationServer(host, port)
        self.meet_participant: MeetParticipant | None = None
        self.current_meet_url: str | None = None

        # メッセージハンドラーを登録
        self._register_handlers()

        # 切断監視フラグ
        self._monitoring_disconnection = False

        # Chrome監視フラグ
        self._monitoring_chrome = False

    def _register_handlers(self) -> None:
        """メッセージハンドラーを登録"""
        self.server.register_handler(MessageType.MEET_URL.value, self._handle_meet_url)
        self.server.register_handler("command", self._handle_command)
        self.server.register_handler("notification", self._handle_notification)

    def _update_gui(
        self,
        status_enum: ConnectionStatus,
        message: str | None = None,
        device: str | None = None,
    ) -> None:
        """GUI更新（GUIがある場合のみ）"""
        if self.gui:
            try:
                self.gui.update_status(status_enum, device)
                if message:
                    self.gui.add_log(message)
            except Exception as e:
                logger.error(f"GUI更新エラー: {e}")

    def _handle_meet_url(self, data: dict[str, Any]) -> None:
        """Meet URL受信処理"""
        meet_url = data.get("content")
        if not meet_url:
            logger.error("Meet URLが含まれていません")
            return

        logger.info(f"Meet URL受信: {meet_url}")
        self.current_meet_url = meet_url
        self._update_gui(
            ConnectionStatus.CONNECTING,
            f"Meet URLを受信: {meet_url}",
            "remote-pc",
        )

        # Meet参加処理
        self._join_meeting(meet_url)

    def _handle_command(self, data: dict[str, Any]) -> None:
        """コマンド処理"""
        command = data.get("content")
        params = data.get("params", {})

        logger.info(f"コマンド受信: {command}")

        if command == RemoteCommand.END_SESSION.value:
            logger.info("リモートPCからセッション終了要求を受信")
            self._update_gui(
                ConnectionStatus.DISCONNECTING, "リモートPCからセッション終了要求を受信"
            )
            self._end_session()
        elif command == "leave_meeting":
            self._leave_meeting()
        elif command == "join_meeting":
            meet_url = params.get("meet_url") or self.current_meet_url
            if meet_url:
                self._join_meeting(meet_url)
            else:
                logger.error("参加するMeet URLが指定されていません")
        elif command == "force_cleanup":
            logger.info("強制クリーンアップ要求を受信")
            self._update_gui(
                ConnectionStatus.DISCONNECTING, "強制クリーンアップ要求を受信"
            )
            self._force_cleanup()
        else:
            logger.warning(f"未知のコマンド: {command}")

    def _handle_notification(self, data: dict[str, Any]) -> None:
        """通知処理"""
        message = data.get("content", "")
        # ハートビートは無視
        if message != MessageType.HEARTBEAT.value:
            logger.info(f"通知: {message}")

    def _join_meeting(self, meet_url: str) -> None:
        """Meetに参加"""
        try:
            logger.info(f"Meetに参加中: {meet_url}")

            # 既存の参加を終了
            if self.meet_participant:
                self.meet_participant.cleanup()

            # 新しい参加者インスタンスを作成（ゲストとして参加）
            self.meet_participant = MeetParticipant(display_name=self.display_name)

            # Meet参加
            if self.meet_participant.join_meeting(meet_url):
                logger.info("Meetへの参加が完了しました")
                self._update_gui(
                    ConnectionStatus.CONNECTED, "Meetへの参加が完了しました"
                )
                notify_usage("フロントPC Meet参加完了", {"Meet URL": meet_url})
                # Chrome監視を開始
                self._start_chrome_monitoring()
            else:
                logger.error("Meetへの参加に失敗しました")
                self._update_gui(ConnectionStatus.ERROR, "Meetへの参加に失敗しました")
                notify_error(
                    Exception("Meet参加失敗"), "Meet参加", {"Meet URL": meet_url}
                )

        except Exception as e:
            logger.error(f"Meet参加エラー: {e}")
            notify_error(e, "Meet参加", {"Meet URL": meet_url})

    def _leave_meeting(self) -> None:
        """Meetから退出"""
        try:
            if self.meet_participant:
                logger.info("Meetから退出中...")
                self.meet_participant.leave_meeting()
                self.meet_participant.cleanup()
                self.meet_participant = None
                logger.info("Meetから退出しました")
            else:
                logger.info("参加中のMeetがありません")
        except Exception as e:
            logger.error(f"Meet退出エラー: {e}")
            notify_error(e, "Meet退出", {})

    def _end_session(self) -> None:
        """セッション終了"""
        logger.info("セッション終了処理を開始...")
        try:
            # リモートPCからの終了コマンドによる処理
            logger.info("リモートPCからの終了要求を受信しました")
            self._leave_meeting()

            # 現在のMeet URLもクリア
            self.current_meet_url = None

            logger.info("セッション終了処理が完了しました")
            self._update_gui(
                ConnectionStatus.WAITING, "セッション終了処理が完了しました"
            )
        except Exception as e:
            logger.error(f"セッション終了処理エラー: {e}")

    def _force_cleanup(self) -> None:
        """強制クリーンアップ処理"""
        logger.info("強制クリーンアップを実行中...")
        try:
            if self.meet_participant:
                self.meet_participant.cleanup()
                self.meet_participant = None
            self.current_meet_url = None
            logger.info("強制クリーンアップが完了しました")
        except Exception as e:
            logger.error(f"強制クリーンアップエラー: {e}")

    def _start_disconnection_monitoring(self) -> None:
        """切断監視を開始"""
        if not self._monitoring_disconnection:
            self._monitoring_disconnection = True
            monitor_thread = threading.Thread(
                target=self._monitor_client_connections, daemon=True
            )
            monitor_thread.start()
            logger.info("クライアント切断監視を開始しました")

    def _monitor_client_connections(self) -> None:
        """クライアント接続を監視"""
        disconnection_time = None

        while self._monitoring_disconnection and self.server.is_running():
            try:
                has_client = len(self.server.clients) > 0

                if not has_client:
                    if disconnection_time is None:
                        disconnection_time = time.time()
                        logger.warning(
                            "リモートクライアントが切断されました。30秒待機中..."
                        )
                    elif time.time() - disconnection_time >= 30:
                        logger.info("リモートクライアントが切断されました")
                        self._handle_all_clients_disconnected()
                        break
                else:
                    if disconnection_time is not None:
                        logger.info("リモートクライアントが再接続されました")
                        disconnection_time = None

                time.sleep(2)

            except Exception as e:
                logger.error(f"切断監視エラー: {e}")
                time.sleep(5)

    def _handle_all_clients_disconnected(self) -> None:
        """全クライアント切断時の処理"""
        logger.info("切断処理を開始: Chromeを終了し待機状態に戻ります")

        try:
            # Meet退出とChrome終了
            if self.meet_participant:
                logger.info("Meetから退出しています...")
                self.meet_participant.leave_meeting()
                self.meet_participant.cleanup()
                self.meet_participant = None
                logger.info("Chromeが終了され、待機状態に戻りました")

            # 現在のMeet URLもクリア
            self.current_meet_url = None

        except Exception as e:
            logger.error(f"切断処理エラー: {e}")

    def _stop_disconnection_monitoring(self) -> None:
        """切断監視を停止"""
        self._monitoring_disconnection = False
        logger.info("クライアント切断監視を停止しました")

    def _start_chrome_monitoring(self) -> None:
        """Chrome監視を開始"""
        if not self._monitoring_chrome:
            self._monitoring_chrome = True
            monitor_thread = threading.Thread(target=self._monitor_chrome, daemon=True)
            monitor_thread.start()
            logger.info("Chrome監視を開始しました")

    def _monitor_chrome(self) -> None:
        """Chromeプロセスを監視"""
        while self._monitoring_chrome and self.meet_participant:
            try:
                if not self.meet_participant.is_chrome_running():
                    logger.info("Chromeが終了されました")
                    self._update_gui(ConnectionStatus.WAITING, "Chromeが終了されました")
                    # Meetから退出処理
                    self._leave_meeting()
                    # 現在のMeet URLもクリア
                    self.current_meet_url = None
                    break

                time.sleep(2)

            except Exception as e:
                logger.error(f"Chrome監視エラー: {e}")
                time.sleep(5)

    def _stop_chrome_monitoring(self) -> None:
        """Chrome監視を停止"""
        self._monitoring_chrome = False
        logger.info("Chrome監視を停止しました")

    def start_reception(self) -> bool:
        """受付サービスを開始"""
        try:
            logger.info("受付サービスを開始します")

            if not self.server.start_server():
                logger.error("サーバーの起動に失敗しました")
                return False

            logger.info(f"受付サービスが開始されました (ポート: {self.port})")
            logger.info("リモートPCからの接続を待機中...")
            self._update_gui(
                ConnectionStatus.WAITING,
                f"サーバーを開始しました (ポート: {self.port})",
            )

            # 切断監視を開始
            self._start_disconnection_monitoring()

            return True

        except Exception as e:
            logger.error(f"受付サービス開始エラー: {e}")
            return False

    def wait_for_requests(self) -> None:
        """リクエスト待機"""
        try:
            logger.info("受付待機中... (Ctrl+Cで終了)")
            while self.server.is_running():
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("終了要求を受信")

    def stop_reception(self) -> None:
        """受付サービスを停止"""
        try:
            logger.info("受付サービスを停止中...")

            # 切断監視を停止
            self._stop_disconnection_monitoring()

            # Chrome監視を停止
            self._stop_chrome_monitoring()

            # Meet退出
            self._leave_meeting()

            # サーバー停止
            self.server.stop_server()

            logger.info("受付サービスを停止しました")

        except Exception as e:
            logger.error(f"受付サービス停止エラー: {e}")

    def run(self) -> None:
        """メイン実行処理"""
        try:
            if self.start_reception():
                self.wait_for_requests()
            else:
                logger.error("受付サービスの開始に失敗しました")
        finally:
            self.stop_reception()
