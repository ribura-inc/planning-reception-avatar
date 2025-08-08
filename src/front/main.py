#!/usr/bin/env python3
"""
フロントPC用メインスクリプト
リモートPCからのMeet URL受信とMeet参加を処理する
"""

import argparse
import logging
import sys
import threading

from src.front.flet_gui import FrontGUI
from src.front.reception_handler import ReceptionHandler
from src.utils.slack import SessionLocation, notify_error, notify_usage

logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システム - フロントPC")
    parser.add_argument("--no-gui", action="store_true", help="GUIなしで実行")
    parser.add_argument(
        "--host", default="0.0.0.0", help="待ち受けホスト (デフォルト: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=9999, help="待ち受けポート (デフォルト: 9999)"
    )
    parser.add_argument(
        "--display-name", default="Reception", help="Meet表示名 (デフォルト: Reception)"
    )
    args = parser.parse_args()

    if args.no_gui:
        # CUIモード
        logger.info("=== VTuber受付システム - フロントPC ===")
        logger.info("受付待機中...")

        handler = ReceptionHandler(
            host=args.host, port=args.port, display_name=args.display_name
        )

        try:
            notify_usage(
                "フロントPC起動", {"ポート": args.port, "表示名": args.display_name},
                location=SessionLocation.FRONT,
            )
            handler.run()
        except KeyboardInterrupt:
            logger.info("終了要求を受信しました")
        except Exception as e:
            logger.error(f"エラー: {e}")
            notify_error(e, "フロントPC メイン処理", {"ポート": args.port}, location=SessionLocation.FRONT)
            sys.exit(1)
        finally:
            handler.stop_reception()
            logger.info("プログラムを終了します")
    else:
        # GUIモード
        gui = FrontGUI()
        handler = None

        def run_handler():
            nonlocal handler
            handler = ReceptionHandler(
                host=args.host,
                port=args.port,
                display_name=args.display_name,
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
            notify_error(e, "フロントPC GUI", {"ポート": args.port}, location=SessionLocation.FRONT)
        finally:
            if handler:
                handler.stop_reception()
            logger.info("プログラムを終了します")


if __name__ == "__main__":
    main()
