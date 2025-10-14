# src

## 🔧 技術スタック

### コア

- **Python**: 3.13+
- **VTube Studio**: アバター制御
- **GCP**: Meet API

### 開発ツール

- **uv**: パッケージ管理
- **Ruff**: Lint・フォーマット

## 🚀 環境構築

### 1. ディレクトリ移動

```sh
cd src
```

### 2. uvのセットアップ

> **備考**: 本リポジトリでは、Pythonのパッケージ管理ツールとして `uv` を採用します。

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 依存関係のインストール

```sh
uv sync
```

### 4. 環境変数設定

```sh
cp .env.example .env
```

## 🧑‍💻 実行方法

### 1. フロントPC側（先に起動）

```bash
python front_pc.py 
```

### 2. リモートPC側（後に起動）

```bash
python remote_pc.py
```

## 🛠️ 開発コマンド

### コード品質

```sh
# Lint チェック
uvx ruff check .

# フォーマット
uvx ruff format .

# 自動修正
uvx ruff check . --fix
```
