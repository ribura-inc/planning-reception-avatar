"""Slack通知機能"""

import os
import traceback
from datetime import datetime
from enum import Enum
from typing import Any

import requests


class NotificationType(Enum):
    """通知タイプ"""

    INFO = "info"  # 使用実績ログ（青色）
    ERROR = "error"  # エラーログ（赤色）


def send_slack_notification(
    notification_type: NotificationType,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
    error_traceback: str | None = None,
) -> None:
    """
    Slack通知を送信

    Args:
        notification_type: 通知タイプ（INFO/ERROR）
        title: 通知タイトル
        message: メインメッセージ
        details: 追加詳細情報（辞書形式）
        error_traceback: エラーのトレースバック情報
    """
    # Webhook URLを環境変数から取得（デフォルト値あり）
    webhook_url = os.getenv(
        "SLACK_WEBHOOK_URL",
        "https://hooks.slack.com/services/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",
    )

    if not webhook_url:
        print(f"Slack Webhook URLが設定されていません: {title} - {message}")
        return

    try:
        # 現在時刻
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ホスト名を取得
        import socket

        hostname = socket.gethostname()

        # 通知タイプに応じた色とアイコン
        if notification_type == NotificationType.INFO:
            color = "#2196F3"  # 青色
            icon = "ℹ️"
            fallback_prefix = "ℹ️"
        else:  # ERROR
            color = "danger"  # 赤色
            icon = "🚨"
            fallback_prefix = "❌"

        # フィールドを構築
        fields = []

        # 詳細情報があれば追加
        if details:
            for key, value in details.items():
                fields.append({"title": key, "value": str(value), "short": True})

        # 基本フィールドを追加
        fields.extend(
            [
                {"title": "ホスト", "value": hostname, "short": True},
                {"title": "実行時刻", "value": now, "short": True},
            ]
        )

        # エラーの場合、トレースバックを追加
        if notification_type == NotificationType.ERROR and error_traceback:
            # トレースバックを制限（Slackの制限対策）
            truncated_traceback = error_traceback[:2000]
            if len(error_traceback) > 2000:
                truncated_traceback += "\n... (truncated)"

            fields.append(
                {
                    "title": "エラー詳細",
                    "value": f"```{truncated_traceback}```",
                    "short": False,
                }
            )

        # ペイロード構築
        payload = {
            "attachments": [
                {
                    "color": color,
                    "fallback": f"{fallback_prefix} {title}: {message}",
                    "title": f"{icon} {title}",
                    "text": message,
                    "fields": fields,
                    "footer": "VTuber Reception System - Ribura Inc.",
                }
            ]
        }

        # Slack Webhook送信
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        # レスポンスチェック
        if response.status_code == 200:
            print(f"Slack通知送信完了: {title} - {message}")
        else:
            print(f"Slack通知送信失敗: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Slack通知送信エラー: {e}")
        # 通知失敗してもメイン処理は継続


def notify_usage(
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """
    使用実績通知を送信するヘルパー関数

    Args:
        action: 実行されたアクション
        details: 追加詳細情報
    """
    send_slack_notification(
        notification_type=NotificationType.INFO,
        title="受付システム利用",
        message=action,
        details=details,
    )


def notify_error(
    error: Exception,
    context: str,
    additional_info: dict[str, Any] | None = None,
) -> None:
    """
    エラー通知を送信するヘルパー関数

    Args:
        error: 発生したエラー
        context: エラーが発生したコンテキスト
        additional_info: 追加情報
    """
    # エラートレースバックを取得
    error_traceback = traceback.format_exc()

    # エラー詳細を構築
    details = {
        "エラー種別": type(error).__name__,
        "コンテキスト": context,
    }

    if additional_info:
        details.update(additional_info)

    send_slack_notification(
        notification_type=NotificationType.ERROR,
        title="受付システムエラー",
        message=str(error),
        details=details,
        error_traceback=error_traceback,
    )
