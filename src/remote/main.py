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

from src.remote.reception_controller import ReceptionController  # noqa: E402


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システム - リモートPC")
    parser.add_argument("--front-ip", required=True, help="フロントPCのIPアドレス")
    parser.add_argument(
        "--skip-extension-check", action="store_true", help="拡張機能チェックをスキップ"
    )
    parser.add_argument(
        "--skip-account-check", action="store_true", help="Googleアカウントチェックをスキップ"
    )

    args = parser.parse_args()

    print("=== VTuber受付システム - リモートPC ===")
    print(f"フロントPC IP: {args.front_ip}")

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
        skip_account_check=args.skip_account_check
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


if __name__ == "__main__":
    main()
