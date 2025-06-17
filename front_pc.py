#!/usr/bin/env python3
"""
フロントPC用実行スクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.front.main import main  # noqa: E402

if __name__ == "__main__":
    main()
