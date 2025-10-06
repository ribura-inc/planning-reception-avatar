# VTuber Reception System

無人ホテルフロント受付システム - VTuberアバターを介した遠隔受付対応

## 概要

ホテルのフロント業務を無人化するためのシステムです。VTube StudioとGoogle Meetを組み合わせ、リモートオペレーターがアバターを介して接客対応を行います。

## システム構成

```mermaid
graph LR
    フロントPC[フロントPC<br>(受付端末)] --> GoogleMeet[Google Meet<br>(通信基盤)]
    リモートPC[リモートPC<br>(制御端末)] --> GoogleMeet
    リモートPC --> VTubeStudio[VTube Studio<br>(アバター制御)]
    リモートPC -.-> Tailscale[Tailscale<br>(P2P通信)]
    フロントPC -.-> Tailscale
```

## 主要機能

1. **完全自動起動**: リモートPCのIPまたは名前指定だけで全自動起動
2. **VTube Studio自動起動**: 未起動時は自動でVTube Studioを起動
3. **高速接続**: 最適化された通信で2秒以内の接続確立
4. **自動終了連動**: リモートPCでChrome終了時、フロントPCも自動終了
5. **プロセス監視**: 異常終了時の自動クリーンアップ
6. **Tailscale統合**: P2P通信による安全で高速な接続

## 使用方法

### 基本的な使用手順

1. **フロントPC起動** (一度起動すれば常時待機)

   ```bash
   # Ryeスクリプト使用（推奨）
   rye run front
   
   # または直接実行
   python -m src.front.main
   ```

2. **リモートPC起動** (フロントPCのIPまたは名前のみ指定)

   ```bash
   # Ryeスクリプト使用（推奨） - IPアドレス指定
   rye run remote 192.168.1.100
   
   # Ryeスクリプト使用（推奨） - Tailscaleデバイス名指定
   rye run remote front-pc-name
   
   # または直接実行
   python -m src.remote.main 192.168.1.100
   python -m src.remote.main front-pc-name
   ```

### GUI版実行（開発・デバッグ用）

```bash
# フロントPC GUI版
rye run front-gui

# リモートPC GUI版  
rye run remote-gui
```

### 高度なオプション

```bash
# 拡張機能チェックをスキップ
python -m src.remote.main front-pc-name --skip-extension-check

# Googleアカウントチェックをスキップ  
python -m src.remote.main front-pc-name --skip-account-check
```

## 自動化フロー

### リモートPC側

1. VTube Studio自動起動確認
2. Meet URL生成
3. フロントPCへ自動接続（最適化済み）
4. Meet URL送信
5. Chrome起動・Meet参加
6. プロセス監視開始
7. 終了時自動クリーンアップ

### フロントPC側

1. 常時待機モード
2. Meet URL自動受信
3. Chrome自動起動・Meet参加
4. プロセス監視開始
5. 終了コマンド受信時自動クリーンアップ

## セットアップ

### 前提条件

- Python 3.11以上
- Rye (パッケージ管理)
- Chrome + 拡張機能:
  - Auto-Admit for Google Meet
- VTube Studio（Windows版 - バーチャルWebカメラ機能を使用）
- Google Cloud Project (Meet API用)
- Tailscale (デバイス名指定時)

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/your-org/planning-reception-avatar.git
cd planning-reception-avatar

# Ryeのインストール (未インストールの場合)
curl -sSf https://rye.astral.sh/get | bash

# 依存関係のインストール
rye sync

# 認証情報の設定
# Google Cloud Consoleからcredentials.jsonをダウンロードしてプロジェクトルートに配置
```

### Chrome拡張機能

以下の拡張機能が必要です：

1. **Auto-Admit for Google Meet**
   - URL: <https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb>
   - 機能: 参加者の自動承認

### VTube Studio設定

VTube StudioのバーチャルWebカメラ機能を有効化してください：

1. VTube Studioを起動
2. 設定からバーチャルWebカメラ機能を有効化
3. カメラ名が「VTube Studio Camera」として登録されることを確認

## ディレクトリ構造

```
src/
├── remote/                    # リモートPC用
│   ├── main.py               # メインエントリーポイント
│   ├── reception_controller.py # 受付制御
│   ├── meet_manager.py       # Meet管理
│   ├── communication_client.py # 通信クライアント
│   └── communication_client_optimized.py # 最適化通信
├── front/                     # フロントPC用
│   ├── main.py               # メインエントリーポイント
│   ├── reception_handler.py  # 受付ハンドラー
│   ├── meet_participant.py   # Meet参加者
│   └── communication_server.py # 通信サーバー
├── utils/                     # 共通ユーティリティ
│   ├── tailscale_utils.py    # Tailscale関連
│   └── vtube_studio_utils.py # VTube Studio関連
└── config.py                # 設定ファイル
```
