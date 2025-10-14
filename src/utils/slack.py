"""Slack通知機能"""

import os
import traceback
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class NotificationType(Enum):
    """通知タイプ"""

    INFO = "info"  # 使用実績ログ（青色）
    ERROR = "error"  # エラーログ（赤色）


class SessionLocation(Enum):
    """セッション実行場所列挙"""

    FRONT = "front"
    REMOTE = "remote"


class MeetEndReason(Enum):
    """Meet終了理由列挙"""

    NORMAL_EXIT = "正常終了（UIの終了ボタン）"
    CHROME_CLOSED = "Chrome強制終了"
    REMOTE_COMMAND = "リモートからのコマンド"
    DISCONNECT = "接続切断"


def send_slack_notification(
    notification_type: NotificationType,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
    error_traceback: str | None = None,
    location: SessionLocation | None = None,
) -> None:
    """Slack通知を送信

    Args:
        notification_type: 通知タイプ（INFO/ERROR）
        title: 通知タイトル
        message: メインメッセージ
        details: 追加詳細情報（辞書形式）
        error_traceback: エラーのトレースバック情報
        location: セッション実行場所（front/remote）
    """
    # Webhook URLを環境変数から取得（デフォルト値あり）
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        return

    try:
        # 現在時刻
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        # 実行場所に応じた絵文字とタイトル
        if location == SessionLocation.FRONT:
            location_emoji = "🏨"
            location_title = "フロントPC"
        elif location == SessionLocation.REMOTE:
            location_emoji = "🧑‍💻"
            location_title = "リモートPC"
        else:
            location_emoji = ""
            location_title = ""

        # 通知タイプに応じた色とアイコン
        color = "#2196F3" if notification_type == NotificationType.INFO else "danger"

        # タイトルの構築（実行場所が指定されている場合は場所情報を先頭に追加）
        display_title = f"{location_emoji} {location_title}" if location else title

        # フィールドを構築
        fields = []

        # 詳細情報があれば追加
        if details:
            for key, value in details.items():
                fields.append({"title": key, "value": str(value), "short": False})

        # 基本フィールドを追加
        fields.extend(
            [
                {"title": "実行時刻", "value": now, "short": False},
            ],
        )

        # エラーの場合、トレースバックを追加
        if notification_type == NotificationType.ERROR and error_traceback:
            # トレースバックを制限（Slackの制限対策）
            max_traceback_len = 2000
            truncated_traceback = error_traceback[:max_traceback_len]
            if len(error_traceback) > max_traceback_len:
                truncated_traceback += "\n... (truncated)"

            fields.append(
                {
                    "title": "エラー詳細",
                    "value": f"```{truncated_traceback}```",
                    "short": False,
                },
            )

        # ペイロード構築
        payload = {
            "attachments": [
                {
                    "color": color,
                    "fallback": f"{display_title}: {message}",
                    "title": display_title,
                    "text": message,
                    "fields": fields,
                    "footer": "VTuber Reception System - Ribura Inc.",
                },
            ],
        }

        # Slack Webhook送信
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        # レスポンスチェック
        http_ok = 200
        if response.status_code == http_ok:
            pass
        else:
            pass

    except Exception:  # noqa: BLE001, S110
        pass
        # 通知失敗してもメイン処理は継続


def notify_usage(
    action: str,
    details: dict[str, Any] | None = None,
    location: SessionLocation | None = None,
) -> None:
    """使用実績通知を送信するヘルパー関数

    Args:
        action: 実行されたアクション
        details: 追加詳細情報
        location: セッション実行場所（front/remote）
    """
    send_slack_notification(
        notification_type=NotificationType.INFO,
        title="受付システム利用",
        message=action,
        details=details,
        location=location,
    )


def notify_meet_end(
    reason: MeetEndReason,
    meet_url: str | None = None,
    additional_info: dict[str, Any] | None = None,
    location: SessionLocation | None = None,
) -> None:
    """Meet終了通知を送信するヘルパー関数

    Args:
        reason: 終了理由
        meet_url: 終了したMeet URL
        additional_info: 追加情報
        location: セッション実行場所（front/remote）
    """
    # 終了理由のメッセージを取得
    reason_message = reason.value

    # 詳細情報を構築
    details = {
        "終了理由": reason.value,
    }

    if meet_url:
        details["Meet URL"] = meet_url

    if additional_info:
        details.update(additional_info)

    send_slack_notification(
        notification_type=NotificationType.INFO,
        title="Meet終了",
        message=f"Meetセッションが終了しました: {reason_message}",
        details=details,
        location=location,
    )


def notify_error(
    error: Exception,
    context: str,
    additional_info: dict[str, Any] | None = None,
    location: SessionLocation | None = None,
) -> None:
    """エラー通知を送信するヘルパー関数

    Args:
        error: 発生したエラー
        context: エラーが発生したコンテキスト
        additional_info: 追加情報
        location: セッション実行場所（front/remote）
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
        location=location,
    )
