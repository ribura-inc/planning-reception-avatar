# VTuber Reception System

無人ホテルフロント受付システム - VTuberアバターを介した遠隔受付対応

## 概要

ホテルのフロント業務を無人化するためのシステムです。VTube StudioとGoogle Meetを組み合わせ、リモートオペレーターがアバターを介して接客対応を行います。

## システム構成

```mermaid
graph LR
    フロントPC[フロントPC<br>(受付端末)] --> GoogleMeet[Google Meet<br>(通信基盤)]
    オペレーターPC[オペレーターPC<br>(制御端末)] --> GoogleMeet
    オペレーターPC --> VTubeStudio[VTube Studio<br>(アバター制御)]
```

## 主要機能

1. **自動接続管理**: Google Meetの24時間制限と熱対策を考慮した接続制御
2. **ワンクリック起動**: オペレーター側からの簡単な呼び出し
3. **アバター連携**: VTube Studioを使用したリアルタイム表情・動作制御
4. **画面共有**: 館内案内や資料表示

## セットアップ

### 前提条件

- Python 3.11以上
- Rye (パッケージ管理)
- Screen Virtual Capture Camera（Chromeの拡張機能）
- VTube Studio（アバター制御）
- Google Cloud Project (Meet API用)

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/your-org/planning-reception-avatar.git
cd planning-reception-avatar

# Ryeのインストール (未インストールの場合)
curl -sSf https://rye.astral.sh/get | bash

# 依存関係のインストール
rye sync

# Google Cloud認証設定
# 1. Google Cloud ConsoleでMeet APIを有効化
# 2. credentials.jsonをプロジェクトルートに配置
# 3. 初回実行時にブラウザで認証
```

### Tailscaleセットアップ（推奨）

異なるネットワーク間でのデバイス通信には[Tailscale](https://tailscale.com)を使用：

```bash
# MacOS
[Tailscale for MacOS](https://tailscale.com/download/mac) からインストーラーをダウンロードしてインストール

# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 接続確認
tailscale status
```

## 使用方法

### 1. フロントPC側（先に起動）

```bash
python front_pc.py --display-name "Hotel Reception"
```

### 2. リモートPC側（後に起動）

```bash
# ローカルネットワーク
python remote_pc.py --front-ip 192.168.1.100

# Tailscale使用時
python remote_pc.py --front-ip my-front-pc
```

### 動作フロー

1. フロントPC起動 → サーバー待機
2. リモートPC起動 → Meet URL生成・送信
3. 両PC自動Meet参加
4. Auto-Admit有効化
5. 受付対応開始
