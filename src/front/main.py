"""
フロントPC用メインスクリプト
リモートPCからのMeet URL受信とMeet参加を処理する
"""

import logging
import threading

from src.front.flet_gui import FrontGUI
from src.front.reception_handler import ReceptionHandler
from src.utils.slack import SessionLocation, notify_error

logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    # デフォルト設定
    host = "0.0.0.0"
    port = 9999
    display_name = "Reception"

    # GUIモード
    gui = FrontGUI()
    handler = None

    def run_handler():
        nonlocal handler
        handler = ReceptionHandler(
            host=host,
            port=port,
            display_name=display_name,
            gui=gui,  # GUIオブジェクトを渡す
        )
        handler.run()

    # ハンドラーをバックグラウンドで実行
    handler_thread = threading.Thread(target=run_handler, daemon=True)
    handler_thread.start()

    # GUIを実行（メインスレッド）
    try:
        gui.run()
    except Exception as e:
        logger.error(f"GUIエラー: {e}")
        notify_error(
            e,
            "フロントPC GUI",
            {"ポート": port},
            location=SessionLocation.FRONT,
        )
    finally:
        if handler:
            handler.stop_reception()
        logger.info("プログラムを終了します")


if __name__ == "__main__":
    main()
