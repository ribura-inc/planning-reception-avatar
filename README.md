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
```
