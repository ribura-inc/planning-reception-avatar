#!/usr/bin/env python3
"""
フロントPC用メインスクリプト
リモートPCからのMeet URL受信とMeet参加を処理する
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.front.reception_handler import ReceptionHandler  # noqa: E402


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システム - フロントPC")
    parser.add_argument(
        "--port", type=int, default=9999, help="リスニングポート (デフォルト: 9999)"
    )
    parser.add_argument(
        "--display-name", default="Reception", help="Meet表示名 (デフォルト: Reception)"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="バインドホスト (デフォルト: 0.0.0.0)"
    )

    args = parser.parse_args()

    print("=== VTuber受付システム - フロントPC ===")
    print(f"リスニングホスト: {args.host}")
    print(f"リスニングポート: {args.port}")
    print(f"Meet表示名: {args.display_name}")
    print()

    # 受付ハンドラーを初期化
    handler = ReceptionHandler(
        host=args.host, port=args.port, display_name=args.display_name
    )

    try:
        # 受付サービスを実行
        handler.run()
    except KeyboardInterrupt:
        print("\n終了要求を受信しました")
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)
    finally:
        handler.stop_reception()
        print("プログラムを終了します")


if __name__ == "__main__":
    main()
