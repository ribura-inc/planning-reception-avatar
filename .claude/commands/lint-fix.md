---
description: format→lint
---

# formatter/linter

src/ の formatter実行 & linterエラー修正を行う

## System Prompt

あなたは経験豊富なソフトウェア開発者として、linterエラーを修正してください。

以下の手順をlintエラーが無くなるまでループして実行してください：

1. **src/ へ移動**
   - `builtin cd src`
2. **format**
   - `uvx ruff format .`
3. **lintエラーの確認**
   - `uvx ruff check . --fix`
   - → なければ終了
4. **lintエラーの適宜修正**
   - すべてを一度に修正する必要はありません。適宜修正しつつ、残りのエラーを次のループで確認してください。
   - 意図的に無視するlintエラーに対しては、 `# noqa: XXX` を使用してOKです
   - ただし、`pyproject.toml`のルールは変更してはいけません
