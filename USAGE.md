# VTuber受付システム - 使用方法

本システムは、リモートPCでMeet URLを生成・送信し、フロントPCで自動参加する仕組みです。

## システム構成

```
[リモートPC]                    [フロントPC]
 ↓ Meet URL生成               ↓ URL受信・Meet参加
 ↓ フロントPCに送信           ↓ 受付対応
 ↓ Meetホスト参加             
 ↓ Auto-Admit有効化           
```

## セットアップ

### 1. 依存関係のインストール

```bash
# Ryeでの依存関係インストール
rye sync
```

### 2. Google Cloud認証設定

1. Google Cloud Consoleで Meet API を有効化
2. `credentials.json` をプロジェクトルートに配置
3. 初回実行時にブラウザで認証

### 3. Auto-Admit拡張機能

リモートPCのChromeに以下の拡張機能をインストール：

- [Auto-Admit for Google Meet](https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb)

## 実行方法

### フロントPC側（先に起動）

```bash
# 基本実行
python front_pc.py

# オプション指定
python front_pc.py --port 9999 --display-name "Hotel Reception"
```

**オプション:**

- `--port`: リスニングポート（デフォルト: 9999）
- `--display-name`: Meet表示名（デフォルト: "Reception"）
- `--host`: バインドホスト（デフォルト: "0.0.0.0"）

### リモートPC側（後に起動）

```bash
# フロントPCのIPアドレスを指定
python remote_pc.py --front-ip 192.168.1.100

# ポート指定
python remote_pc.py --front-ip 192.168.1.100 --port 9999
```

**オプション:**

- `--front-ip`: フロントPCのIPアドレス（必須）
- `--port`: 通信ポート（デフォルト: 9999）

## 動作フロー

1. **フロントPC起動**: サーバーを起動してリモートPCからの接続を待機
2. **リモートPC起動**: Meet URL生成 → フロントPCに送信
3. **自動Meet参加**: 両PCが自動的にMeetに参加
4. **Auto-Admit有効**: リモートPCで自動承認を有効化
5. **受付対応開始**: システム準備完了

## トラブルシューティング

### 接続エラー

```bash
# フロントPCのファイアウォール確認
# ポート9999が開放されているか確認

# ネットワーク接続確認
ping [フロントPCのIP]
telnet [フロントPCのIP] 9999
```

### Meet参加失敗

1. **Googleアカウント**: 同一アカウントでログイン確認
2. **拡張機能**: Auto-Admitが正しくインストールされているか
3. **ブラウザプロファイル**: `.chrome-profile-*` ディレクトリのクリア

### 認証エラー

```bash
# 認証情報をリセット
rm token.json
# 再実行時に再認証
```

## ファイル構成

```
src/
├── remote/           # リモートPC用モジュール
│   ├── meet_manager.py       # Meet管理
│   ├── communication_client.py # 通信クライアント
│   ├── reception_controller.py # メインコントローラー
│   └── main.py              # エントリーポイント
├── front/            # フロントPC用モジュール
│   ├── meet_participant.py     # Meet参加
│   ├── communication_server.py # 通信サーバー
│   ├── reception_handler.py    # 受付ハンドラー
│   └── main.py              # エントリーポイント
remote_pc.py             # リモートPC実行スクリプト
front_pc.py             # フロントPC実行スクリプト
```

## 開発者向け

### ログレベル変更

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### カスタマイズ

- `MeetManager`: Meet URL生成ロジック
- `CommunicationClient/Server`: 通信プロトコル
- `MeetParticipant`: Meet参加動作
- `ReceptionController/Handler`: 全体制御ロジック
