"""共通エラーハンドリングユーティリティ

想定外のエラーをSlack通知するための仕組みを提供します。
"""

import sys
import traceback
from typing import Any

from src.utils.slack import NotificationType, SessionLocation, send_slack_notification


def handle_uncaught_exception(
    location: SessionLocation,
    app_name: str,
) -> None:
    """キャッチされなかった例外をSlack通知する最終防衛ライン

    Args:
        location: 実行場所（FRONT/REMOTE）
        app_name: アプリケーション名

    使用例:
        def main():
            try:
                # メイン処理
                pass
            except Exception as exc:
                handle_uncaught_exception(SessionLocation.REMOTE, "リモートPC")
                raise
    """

    def exception_hook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        """sys.excepthookに設定する例外ハンドラー"""
        # KeyboardInterrupt等は通常通り処理
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # トレースバックを文字列化
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        error_traceback = "".join(tb_lines)

        # Slack通知
        send_slack_notification(
            notification_type=NotificationType.ERROR,
            title=f"{app_name}で未処理の例外が発生",
            message=f"{exc_type.__name__}: {exc_value}",
            details={
                "アプリケーション": app_name,
            },
            error_traceback=error_traceback,
            location=location,
        )

        # デフォルトの例外処理を実行（エラー表示）
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook
