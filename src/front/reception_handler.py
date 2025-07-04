"""
受付ハンドラー（フロントPC用）
リモートPCからの指示を受けてMeet参加などを処理する
"""

import logging
import time
from typing import Any

from .communication_server import CommunicationServer
from .meet_participant import MeetParticipant

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReceptionHandler:
    """フロントPC用受付処理ハンドラー"""

    def __init__(
        self, host: str = "0.0.0.0", port: int = 9999, display_name: str = "Reception"
    ):
        """
        Args:
            host: サーバーのホスト
            port: サーバーのポート
            display_name: Meet表示名
        """
        self.host = host
        self.port = port
        self.display_name = display_name

        # コンポーネント初期化
        self.server = CommunicationServer(host, port)
        self.meet_participant: MeetParticipant | None = None
        self.current_meet_url: str | None = None

        # メッセージハンドラーを登録
        self._register_handlers()

    def _register_handlers(self) -> None:
        """メッセージハンドラーを登録"""
        self.server.register_handler("meet_url", self._handle_meet_url)
        self.server.register_handler("command", self._handle_command)
        self.server.register_handler("notification", self._handle_notification)

    def _handle_meet_url(self, data: dict[str, Any]) -> None:
        """Meet URL受信処理"""
        meet_url = data.get("content")
        if not meet_url:
            logger.error("Meet URLが含まれていません")
            return

        logger.info(f"Meet URL受信: {meet_url}")
        self.current_meet_url = meet_url

        # Meet参加処理
        self._join_meeting(meet_url)

    def _handle_command(self, data: dict[str, Any]) -> None:
        """コマンド処理"""
        command = data.get("content")
        params = data.get("params", {})

        logger.info(f"コマンド受信: {command}")

        if command == "end_session":
            self._end_session()
        elif command == "leave_meeting":
            self._leave_meeting()
        elif command == "join_meeting":
            meet_url = params.get("meet_url") or self.current_meet_url
            if meet_url:
                self._join_meeting(meet_url)
            else:
                logger.error("参加するMeet URLが指定されていません")
        else:
            logger.warning(f"未知のコマンド: {command}")

    def _handle_notification(self, data: dict[str, Any]) -> None:
        """通知処理"""
        message = data.get("content", "")
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
            else:
                logger.error("Meetへの参加に失敗しました")

        except Exception as e:
            logger.error(f"Meet参加エラー: {e}")

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

    def _end_session(self) -> None:
        """セッション終了"""
        logger.info("セッション終了処理を開始...")
        self._leave_meeting()
        logger.info("セッション終了処理が完了しました")


    def start_reception(self) -> bool:
        """受付サービスを開始"""
        try:
            logger.info("受付サービスを開始します")

            if not self.server.start_server():
                logger.error("サーバーの起動に失敗しました")
                return False

            logger.info(f"受付サービスが開始されました (ポート: {self.port})")
            logger.info("リモートPCからの接続を待機中...")

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
