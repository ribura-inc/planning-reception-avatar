# CLAUDE.md

このファイルは、Claude Code用のAI専用指示です。人間が参照すべきドキュメントは適宜別ファイルで作成し、AIにも @path/to/import の構文を使用してインポートすること。

## コア

- Always Think in English, but respond in Japanese.
- For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially.
- MUST use subagents for complex problem verification
- After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding. Use your thinking to plan and iterate based on this new information, and then take the best next action.
- Do what has been asked; nothing more, nothing less.
- NEVER create files unless they're absolutely necessary for achieving your goal.
- ALWAYS prefer editing an existing file to creating a new one.

## プロジェクトコンテキスト参照

開発前に以下のドキュメントを必ず参照してください：

- **プロジェクト概要・セットアップ**: @README.md

## AI開発フロー

### 1. 開発前

- TodoWriteでタスク分割・管理
- 関連ドキュメントを参照して仕様理解
- 既存コードパターンを確認

### 2. 実装

- 実装は `src/` ディレクトリ配下で行う
- すべてのインポートは `from src.xxx` の形式で記述
- プロジェクトルートから `uv run python -m src.xxx.main` で実行

### 3. 品質保証（必須）

- 全実装後に必ず実行：

```bash
# コード品質チェック（プロジェクトルートで実行）
uvx ruff check . --fix
uvx ruff format .
```

### 4. ドキュメント更新

- 既存のドキュメントでアップデートすべき箇所があれば修正
- 新たにドキュメントで残した方が良い事項があれば作成

## AI専用制約

### 厳守事項

- **型安全性**: PythonのType Annotationを全てで利用する（python3.13を利用しているので、 `from typing import List, Dict` は使用せず、 `list`, `dict` でよい）
- **品質チェック**: Lintエラーは必ず修正してから完了報告

### ドキュメント保守ルール

- 新機能追加時：関連ドキュメントを更新
- アーキテクチャ変更時：CLAUDE.mdとREADME.mdを更新

### 開発判断基準

- 既存パターンに従う（新規パターン作成は避ける）
- コミットしない（明示的指示がない限り）
