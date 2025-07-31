#!/usr/bin/env python3
"""
リモートPC用メインスクリプト
Meet URL生成・送信とホスト処理を実行する
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.models.enums import ConnectionStatus  # noqa: E402
from src.remote.flet_gui import RemoteGUI  # noqa: E402
from src.remote.reception_controller import ReceptionController  # noqa: E402


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システム - リモートPC")
    parser.add_argument(
        "front_ip", nargs="?", help="フロントPCのIPアドレスまたはTailscaleデバイス名"
    )
    parser.add_argument(
        "--no-gui", action="store_true", help="GUIなしで実行"
    )
    parser.add_argument(
        "--skip-extension-check", action="store_true", help="拡張機能チェックをスキップ"
    )
    parser.add_argument(
        "--skip-account-check",
        action="store_true",
        help="Googleアカウントチェックをスキップ",
    )

    args = parser.parse_args()

    # CUIモードまたはfront_ipが指定されている場合
    if args.no_gui or args.front_ip:
        if not args.front_ip:
            print("エラー: --no-guiモードではfront_ipが必要です")
            sys.exit(1)

        print("=== VTuber受付システム - リモートPC ===")
        print(f"フロントPC: {args.front_ip}")

        if args.skip_extension_check:
            print("注意: 拡張機能チェックをスキップします")
        if args.skip_account_check:
            print("注意: Googleアカウントチェックをスキップします")
        print()

        # 受付コントローラーを初期化（固定ポート9999）
        controller = ReceptionController(
            args.front_ip,
            9999,
            skip_extension_check=args.skip_extension_check,
            skip_account_check=args.skip_account_check,
        )

        try:
            # 受付セッションを実行
            controller.run()
        except KeyboardInterrupt:
            print("\n終了要求を受信しました")
        except Exception as e:
            print(f"エラー: {e}")
            sys.exit(1)
        finally:
            controller.cleanup()
            print("プログラムを終了します")
    else:
        # GUIモード
        gui = RemoteGUI()
        controller = None

        def connect_to_front(front_ip: str):
            nonlocal controller
            try:
                gui.update_status(ConnectionStatus.CONNECTING.value)
                gui.add_log(f"{front_ip} への接続を開始...")

                # コントローラーを初期化
                controller = ReceptionController(
                    front_ip,
                    9999,
                    skip_extension_check=args.skip_extension_check,
                    skip_account_check=args.skip_account_check,
                    gui=gui  # GUIオブジェクトを渡す
                )

                # 接続開始
                if controller.start_reception_session():
                    gui.update_status("セッション中", front_ip)
                    gui.add_log("セッションが開始されました")
                    # セッション監視
                    controller.wait_for_chrome_exit()
                    gui.update_status(ConnectionStatus.NOT_CONNECTED.value)
                    gui.add_log("セッションが終了しました")
                else:
                    gui.update_status(ConnectionStatus.ERROR.value)
                    gui.add_log("接続に失敗しました")

            except Exception as e:
                gui.update_status(ConnectionStatus.ERROR.value)
                gui.add_log(f"エラー: {e}")
            finally:
                if controller:
                    controller.cleanup()
                    controller = None

        def disconnect_session():
            if controller:
                gui.add_log("セッションを終了しています...")
                controller.end_session()
                controller.cleanup()

        gui.set_connect_callback(connect_to_front)
        gui.set_disconnect_callback(disconnect_session)

        # GUIを実行
        try:
            gui.run()
        except Exception as e:
            print(f"GUIエラー: {e}")
        finally:
            if controller:
                controller.cleanup()
            print("プログラムを終了します")


if __name__ == "__main__":
    main()
