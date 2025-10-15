# VTuber Reception System

## 🎯 プロジェクトについて

- クライアント：プランニングオフィス株式会社
- フェーズ：1拠点での動作確認（プランニングは3拠点のホテルを構える）
- システム名：VTuber受付システム
- システム概要：ホテルのフロント業務を無人化するためのシステムです。VTube StudioとGoogle Meetを組み合わせ、リモートオペレーターがアバターを介して接客対応を行います。


## 📚 ドキュメント

-

## 🚀 環境構築

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd planning-reception-avatar
```

### 2. lefthookのセットアップ

- lefthookをグローバルにインストールしてください。詳細なインストール手順は [lefthook公式ドキュメント](https://lefthook.dev/installation/index.html) をご確認ください。
  - macOS (Homebrew)

    ```bash
    brew install lefthook
    ```

  - Linux (Debian/Ubuntu)

    ```bash
    sudo apt install lefthook
    ```

  - Node.js (グローバル)

    ```bash
    npm install -g lefthook
    ```

- セットアップ完了後、下記のコマンドを実行することで、`.git/hooks/` に hooks の設定が自動インストールされます。

    ```bash
    lefthook install
    ```

    > **補足**: `lefthook.yaml` を修正した場合は、再度 `lefthook install` を実行して設定を反映してください。

### 3. serenaのセットアップ（claude利用者）

> **注意**: 2025/09/20時点では、serena を導入したほうが claude の性能が上がると評判にある

```sh
claude mcp add serena -- uvx --from git+https://github.com/oraios/serena serena-mcp-server --context ide-assistant --project $(pwd)
```

### 4. Tailscaleセットアップ

異なるネットワーク間でのデバイス通信には[Tailscale](https://tailscale.com)を使用：

```bash
# MacOS
[Tailscale for MacOS](https://tailscale.com/download/mac) からインストーラーをダウンロードしてインストール

# Windows
TODO

# 接続確認
tailscale status
```

### 5. uvのセットアップ

本リポジトリでは、Pythonのパッケージ管理ツールとして `uv` を採用します。

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 6. 依存関係のインストール

プロジェクトルートで実行：

```sh
uv sync
```

### 7. 環境変数設定

プロジェクトルートで実行：

```sh
cp .env.example .env
```

### 8. VTube Studioのインストール

- VTube Studioをインストールしてください。
- バーチャルWEBカメラ機能を用いて、VTube Studioのアバター画面をカメラとして用います。
  - MacではVTube Studioのバーチャルカメラが利用できない → 素のカメラで動作確認

## 🔧 技術スタック

### コア

- **Python**: 3.13+
- **VTube Studio**: アバター制御
- **GCP**: Meet API

### 開発ツール

- **uv**: パッケージ管理
- **Ruff**: Lint・フォーマット

## 🧑‍💻 実行方法

プロジェクトルートから実行してください。

### 1. フロントPC側（先に起動）

```bash
uv run python -m src.front.main
```

### 2. リモートPC側（後に起動）

```bash
uv run python -m src.remote.main
```

## 🛠️ 開発コマンド

### コード品質

プロジェクトルートで実行：

```sh
# Lint チェック
uvx ruff check .

# フォーマット
uvx ruff format .

# 自動修正
uvx ruff check . --fix
```
