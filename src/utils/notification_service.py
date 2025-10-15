"""最新の通知ポリシーに沿った高水準ヘルパー群。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .slack import SessionLocation, notify_error, notify_usage


@dataclass(slots=True)
class BaseNotifier:
    """Slack通知送信を簡潔にする共通ベースクラス。"""

    location: SessionLocation

    def _usage(self, action: str, details: dict[str, Any] | None = None) -> None:
        notify_usage(action, details=details, location=self.location)

    def _error(self, error: Exception, context: str, detail: dict[str, Any] | None = None) -> None:
        notify_error(error, context=context, additional_info=detail, location=self.location)


class FrontNotifier(BaseNotifier):
    """フロントアプリ専用の通知フロー。"""

    def app_started(self) -> None:
        self._usage("フロントアプリ起動", {})

    def app_stopped(self) -> None:
        self._usage("フロントアプリ終了", {})

    def report_error(self, error: Exception, context: str, detail: dict[str, Any] | None = None) -> None:
        self._error(error, context=context, detail=detail)

    def room_entry_complete(self, meet_url: str) -> None:
        """入室完了通知を送信

        Args:
            remote_device: リモートデバイス名
            meet_url: Meet URL
        """
        details = {}
        if meet_url:
            details["Meet URL"] = meet_url
        self._usage("リモート接続完了", details)


class RemoteNotifier(BaseNotifier):
    """リモートアプリ専用の通知フロー。"""

    def app_started(self) -> None:
        self._usage("リモートアプリ起動", {})

    def disconnect_complete(self, front_device: str) -> None:
        self._usage("リモート切断完了", {"接続先": front_device})

    def app_stopped(self) -> None:
        self._usage("リモートアプリ終了", {})

    def report_error(self, error: Exception, context: str, detail: dict[str, Any] | None = None) -> None:
        self._error(error, context=context, detail=detail)
