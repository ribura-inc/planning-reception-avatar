#!/usr/bin/env python3
"""
フロントPC用メインスクリプト
リモートPCからのMeet URL受信とMeet参加を処理する
"""

import argparse
import sys
import threading
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.front.flet_gui import FrontGUI  # noqa: E402
from src.front.reception_handler import ReceptionHandler  # noqa: E402


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システム - フロントPC")
    parser.add_argument("--no-gui", action="store_true", help="GUIなしで実行")
    parser.add_argument("--host", default="0.0.0.0", help="待ち受けホスト (デフォルト: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9999, help="待ち受けポート (デフォルト: 9999)")
    parser.add_argument("--display-name", default="Reception", help="Meet表示名 (デフォルト: Reception)")
    args = parser.parse_args()

    if args.no_gui:
        # CUIモード
        print("=== VTuber受付システム - フロントPC ===")
        print("受付待機中...")

        handler = ReceptionHandler(
            host=args.host,
            port=args.port,
            display_name=args.display_name
        )

        try:
            handler.run()
        except KeyboardInterrupt:
            print("\n終了要求を受信しました")
        except Exception as e:
            print(f"エラー: {e}")
            sys.exit(1)
        finally:
            handler.stop_reception()
            print("プログラムを終了します")
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
                gui=gui  # GUIオブジェクトを渡す
            )
            handler.run()

        # ハンドラーをバックグラウンドで実行
        handler_thread = threading.Thread(target=run_handler, daemon=True)
        handler_thread.start()

        # GUIを実行（メインスレッド）
        try:
            gui.run()
        except Exception as e:
            print(f"GUIエラー: {e}")
        finally:
            if handler:
                handler.stop_reception()
            print("プログラムを終了します")


if __name__ == "__main__":
    main()
