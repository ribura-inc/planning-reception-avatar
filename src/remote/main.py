"""
リモートPC用メインスクリプト
Meet URL生成・送信とホスト処理を実行する
"""

import logging
import threading

from src.models.enums import ConnectionStatus
from src.remote.flet_gui import RemoteGUI
from src.remote.reception_controller import ReceptionController
from src.utils.slack import SessionLocation, notify_error

logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    # GUIモード
    gui = RemoteGUI()
    controller = None

    def connect_to_front(front_ip: str):
        nonlocal controller
        try:
            gui.update_status(ConnectionStatus.CONNECTING)
            gui.add_log(f"{front_ip} への接続を開始...")

            # コントローラーを初期化
            controller = ReceptionController(
                front_ip,
                9999,
                gui=gui,  # GUIオブジェクトを渡す
            )

            # 接続開始
            if controller.start_reception_session():
                gui.update_status(ConnectionStatus.CONNECTED)
                gui.add_log("セッションが開始されました")

                # バックグラウンドでセッション監視を開始
                def monitor_session():
                    nonlocal controller
                    controller.wait_for_session_end()
                    # セッション終了後の処理
                    controller.cleanup()
                    controller = None

                monitor_thread = threading.Thread(target=monitor_session, daemon=True)
                monitor_thread.start()
            else:
                gui.update_status(ConnectionStatus.ERROR)
                gui.add_log("接続に失敗しました")
                controller = None

        except Exception as e:
            gui.update_status(ConnectionStatus.ERROR)
            gui.add_log(f"エラー: {e}")
            notify_error(
                e,
                "リモートPC GUI接続",
                {"フロントPC": front_ip},
                location=SessionLocation.REMOTE,
            )

    def disconnect_session():
        nonlocal controller
        if controller:
            gui.add_log("セッションを終了しています...")
            controller.cleanup()
            controller = None

    gui.set_connect_callback(connect_to_front)
    gui.set_disconnect_callback(disconnect_session)

    # GUIを実行
    try:
        gui.run()
    except Exception as e:
        logger.error(f"GUIエラー: {e}")
    finally:
        if controller:
            controller.cleanup()
        logger.info("プログラムを終了します")


if __name__ == "__main__":
    main()
