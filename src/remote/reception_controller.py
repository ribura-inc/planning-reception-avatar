"""
受付コントローラー（リモートPC用）
Meet URL生成・送信とホスト処理を統合管理する
"""

import logging
import time

from ..utils.vtube_studio_utils import check_and_setup_vtube_studio
from .communication_client import CommunicationClient
from .meet_manager import MeetManager

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReceptionController:
    """受付システムのメインコントローラー"""

    def __init__(
        self,
        front_pc_ip: str,
        port: int = 9999,
        skip_extension_check: bool = False,
        skip_account_check: bool = False,
    ):
        """
        Args:
            front_pc_ip: フロントPCのIPアドレスまたはTailscaleデバイス名
            port: 通信ポート
            skip_extension_check: 拡張機能チェックをスキップ
            skip_account_check: Googleアカウントチェックをスキップ
        """
        self.front_pc_ip = front_pc_ip
        self.port = port
        self.skip_extension_check = skip_extension_check
        self.skip_account_check = skip_account_check
        self.meet_manager = MeetManager()

        # 最適化された通信クライアントを使用（デフォルト）
        self.communication_client = CommunicationClient(front_pc_ip, port)

        self.current_meet_url: str | None = None
        self._session_ended: bool = False

    def _handle_chrome_exit(self) -> None:
        """Chrome終了時の処理"""
        logger.info("Chrome終了を検知しました")
        try:
            # フロントPCに終了通知を送信
            if self.communication_client.is_connected():
                logger.info("フロントPCに終了通知を送信中...")
                self.communication_client.send_command("end_session")
                time.sleep(1)  # 送信完了を待つ

            # セッション終了フラグを立てる
            self._session_ended = True
        except Exception as e:
            logger.error(f"Chrome終了処理エラー: {e}")

    def start_reception_session(self) -> bool:
        """受付セッションを開始"""
        try:
            logger.info("受付セッションを開始します")
            self._session_ended = False

            # 0. VTube Studio状態確認
            logger.info("VTube Studioの状態を確認中...")
            vtube_ok, vtube_message = check_and_setup_vtube_studio()
            if not vtube_ok:
                logger.error(f"VTube Studio確認失敗: {vtube_message}")
                return False
            logger.info(f"VTube Studio確認成功: {vtube_message}")

            # 1. Meet URL生成
            logger.info("Meet URLを生成中...")
            self.current_meet_url = self.meet_manager.create_meet_space()

            # 2. フロントPCに接続
            logger.info("フロントPCに接続中...")
            if not self.communication_client.connect():
                logger.error("フロントPCに接続できませんでした")
                return False

            # 3. Meet URLをフロントPCに送信
            logger.info("Meet URLをフロントPCに送信中...")
            if not self.communication_client.send_meet_url(self.current_meet_url):
                logger.error("Meet URL送信に失敗しました")
                return False

            # 4. ブラウザセットアップ
            logger.info("ブラウザをセットアップ中...")
            self.meet_manager.setup_browser()

            # Chrome終了時のコールバックを設定
            self.meet_manager.set_chrome_exit_callback(self._handle_chrome_exit)

            # 5. Googleログイン確認
            if not self.skip_account_check:
                logger.info("Googleアカウントのログインを確認中...")
                self.meet_manager.ensure_google_login()
            else:
                logger.info("Googleアカウントチェックをスキップしました")

            # 6. 拡張機能の確認
            if not self.skip_extension_check:
                logger.info("拡張機能の確認中...")

                # Auto-Admit拡張機能の確認
                if not self.meet_manager.check_extension(
                    self.meet_manager.AUTO_ADMIT_EXTENSION_URL, "Auto-Admit"
                ):
                    logger.error("Auto-Admit拡張機能がインストールされていません")
                    logger.error(
                        f"次のURLから手動でインストールしてください: {self.meet_manager.AUTO_ADMIT_EXTENSION_URL}"
                    )
                    return False

                # Screen Capture Virtual Camera拡張機能の確認
                if not self.meet_manager.check_extension(
                    self.meet_manager.SCREEN_CAPTURE_EXTENSION_URL,
                    "Screen Capture Virtual Camera",
                ):
                    logger.error(
                        "Screen Capture Virtual Camera拡張機能がインストールされていません"
                    )
                    logger.error(
                        f"次のURLから手動でインストールしてください: {self.meet_manager.SCREEN_CAPTURE_EXTENSION_URL}"
                    )
                    return False
            else:
                logger.info("拡張機能チェックをスキップしました")

            # 7. Meetにホストとして参加
            logger.info("Meetにホストとして参加中...")
            self.meet_manager.join_as_host(self.current_meet_url)

            # 8. Auto-Admit機能有効化
            logger.info("Auto-Admit機能を有効化中...")
            self.meet_manager.enable_auto_admit()

            # 9. Chrome プロセス監視を開始
            logger.info("Chromeプロセス監視を開始中...")
            self.meet_manager.start_process_monitoring()

            # 10. フロントPCに準備完了通知
            self.communication_client.send_notification("受付システム準備完了")

            logger.info("受付セッションの開始が完了しました")
            logger.info(f"Meet URL: {self.current_meet_url}")

            return True

        except Exception as e:
            logger.error(f"受付セッション開始エラー: {e}")
            self.cleanup()
            return False

    def wait_for_session_end(self) -> None:
        """セッション終了まで待機"""
        try:
            logger.info("受付セッション中... (Ctrl+Cで終了)")
            while True:
                time.sleep(1)

                # セッション終了フラグのチェック
                if self._session_ended:
                    logger.info("Chrome終了により自動でセッションを終了します")
                    break

                # Meetセッション状態チェック（従来の方法も残す）
                if not self.meet_manager.is_session_active():
                    logger.info(
                        "Chromeが終了またはMeetから退出したため、セッションを終了します"
                    )
                    break

                # 通信チェック
                if not self.communication_client.is_connected():
                    logger.warning("フロントPCとの通信が切断されました")
                    break

        except KeyboardInterrupt:
            logger.info("セッション終了要求を受信")
        except Exception as e:
            logger.error(f"セッション中エラー: {e}")

    def end_reception_session(self) -> None:
        """受付セッションを終了"""
        try:
            logger.info("受付セッションを終了中...")

            # フロントPCに終了通知
            if self.communication_client.is_connected():
                self.communication_client.send_command("end_session")

            self.cleanup()
            logger.info("受付セッションを終了しました")

        except Exception as e:
            logger.error(f"セッション終了エラー: {e}")

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        try:
            self.meet_manager.cleanup()
            self.communication_client.disconnect()
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")

    def run(self) -> None:
        """メイン実行処理"""
        try:
            if self.start_reception_session():
                self.wait_for_session_end()
            else:
                logger.error("受付セッションの開始に失敗しました")
        finally:
            self.end_reception_session()
