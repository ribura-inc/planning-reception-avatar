# VTuber受付システム ビルドガイド

このドキュメントでは、VTuber受付システムをWindows/Mac用の実行ファイル（.exe/.app）にビルドする方法を説明します。

## 🚀 クイックスタート

```bash
# 両方のアプリケーションをビルド
rye run build

# フロントアプリのみビルド
rye run build-front

# リモートアプリのみビルド
rye run build-remote

# クリーンビルド（以前のビルド結果を削除してから）
rye run build-clean
```

## 📋 前提条件

- Python 3.11以上
- Rye（パッケージ管理ツール）
- Google Cloud credentials.json（オプション - Meet機能使用時）

## 🛠️ セットアップ

### 1. credentials.jsonの配置（オプション）

Google Meet機能を使用する場合は、Google Cloud Consoleからダウンロードした`credentials.json`をプロジェクトルートに配置してください。

```
planning-reception-avatar/
├── credentials.json  ← ここに配置
├── front.spec
├── remote.spec
└── build.py
```

## 🏗️ ビルド方法

### 基本的なビルド

```bash
# すべてをビルド
python build.py

# または
rye run build
```

### 個別ビルド

```bash
# フロントアプリケーションのみ
python build.py --target front

# リモートアプリケーションのみ
python build.py --target remote
```

### オプション

```bash
# クリーンビルド（古いビルド結果を削除）
python build.py --clean

# 事前チェックをスキップ
python build.py --no-check
```

## 📦 ビルド結果

ビルド完了後、`dist/`フォルダに実行ファイルが生成されます：

### macOS

```
dist/
├── VTuber受付システム_フロント.app
└── VTuber受付システム_リモート.app
```

### Windows

```
dist/
├── VTuberReceptionFront.exe
└── VTuberReceptionRemote.exe
```

## 🖥️ 実行方法

### macOS

**方法1: Finderから**

1. `dist`フォルダを開く
2. `.app`ファイルをダブルクリック

**方法2: ターミナルから**

```bash
open dist/VTuber受付システム_フロント.app
open dist/VTuber受付システム_リモート.app
```

### Windows

**方法1: エクスプローラーから**

1. `dist`フォルダを開く
2. `.exe`ファイルをダブルクリック

**方法2: コマンドプロンプトから**

```cmd
dist\VTuberReceptionFront.exe
dist\VTuberReceptionRemote.exe
```

## 🎨 アイコンについて

`assets/`フォルダに以下のアイコンファイルが含まれています：

- `icon.icns` - macOS用アイコン
- `icon.ico` - Windows用アイコン
- `icon.png` - その他のOS用アイコン

これらは自動的にビルド時に適用されます。

## ⚠️ 注意事項

### 初回起動時の警告（macOS）

macOSでは、初回起動時に「開発元が未確認」の警告が表示される場合があります。

**解決方法:**

1. システム環境設定 → セキュリティとプライバシー
2. 「このまま開く」をクリック

または、右クリック → 「開く」を選択

### Windows Defenderの警告

Windowsでは、Windows Defenderが警告を表示する場合があります。

**解決方法:**
「詳細情報」→「実行する」を選択

### credentials.jsonについて

- ビルド時に`credentials.json`がない場合でもビルドは成功します
- Google Meet機能を使用する際は、実行時に設定が必要になります
- セキュリティのため、`credentials.json`は実行ファイルに含めないことを推奨します
