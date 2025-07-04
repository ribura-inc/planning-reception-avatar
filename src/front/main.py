#!/usr/bin/env python3
"""
フロントPC用メインスクリプト
リモートPCからのMeet URL受信とMeet参加を処理する
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.front.reception_handler import ReceptionHandler  # noqa: E402


def main():
    """メイン処理"""
    # シンプルな設定（オプション削減）
    print("=== VTuber受付システム - フロントPC ===")
    print("受付待機中...")

    # 受付ハンドラーを初期化（固定設定）
    handler = ReceptionHandler(
        host="0.0.0.0", port=9999, display_name="Reception"
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
