#!/usr/bin/env python3
"""
リモートPC用メインスクリプト
Meet URL生成・送信とホスト処理を実行する
"""

import argparse
import logging
import sys

from src.models.enums import ConnectionStatus
from src.remote.flet_gui import RemoteGUI
from src.remote.reception_controller import ReceptionController
from src.utils.slack import SessionLocation, notify_error

logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システム - リモートPC")
    parser.add_argument(
        "front_ip", nargs="?", help="フロントPCのIPアドレスまたはTailscaleデバイス名"
    )
    parser.add_argument("--no-gui", action="store_true", help="GUIなしで実行")

    args = parser.parse_args()

    # CUIモードまたはfront_ipが指定されている場合
    if args.no_gui or args.front_ip:
        if not args.front_ip:
            logger.error("エラー: --no-guiモードではfront_ipが必要です")
            sys.exit(1)

        logger.info("=== VTuber受付システム - リモートPC ===")
        logger.info(f"フロントPC: {args.front_ip}")

        logger.info("")

        # 受付コントローラーを初期化（固定ポート9999）
        controller = ReceptionController(
            args.front_ip,
            9999,
        )

        try:
            # 受付セッションを実行
            controller.run()
        except KeyboardInterrupt:
            logger.info("終了要求を受信しました")
        except Exception as e:
            logger.error(f"エラー: {e}")
            notify_error(
                e,
                "リモートPC メイン処理",
                {"フロントPC": args.front_ip},
                location=SessionLocation.REMOTE,
            )
            sys.exit(1)
        finally:
            controller.cleanup()
            logger.info("プログラムを終了します")
    else:
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
                    import threading

                    def monitor_session():
                        nonlocal controller
                        controller.wait_for_session_end()
                        # セッション終了後の処理
                        controller.cleanup()
                        controller = None

                    monitor_thread = threading.Thread(
                        target=monitor_session, daemon=True
                    )
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
