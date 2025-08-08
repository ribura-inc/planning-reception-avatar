"""
Pydantic モデル定義
データの検証と型安全性を確保
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ConnectionStatus, MessageType, RemoteCommand

# ------------------------------------------------------------
# メッセージ
# ------------------------------------------------------------


class CommunicationMessage(BaseModel):
    """通信メッセージの基本構造"""

    model_config = ConfigDict(use_enum_values=True)

    type: MessageType
    content: str | None = None
    params: dict[str, Any] | None = None


class MeetURLMessage(CommunicationMessage):
    """Meet URL送信メッセージ"""

    type: MessageType = MessageType.MEET_URL
    content: str | None = Field(default=None, description="Google Meet URL")

    @field_validator("content")
    @classmethod
    def validate_meet_url(cls, v: str | None) -> str | None:
        """Meet URLの妥当性を検証"""
        if v is not None and not v.startswith("https://meet.google.com/"):
            raise ValueError("Invalid Meet URL format")
        return v


class CommandMessage(CommunicationMessage):
    """コマンドメッセージ"""

    type: MessageType = MessageType.COMMAND
    content: str | None = None
    command: RemoteCommand | None = None


class NotificationMessage(CommunicationMessage):
    """通知メッセージ"""

    type: MessageType = MessageType.NOTIFICATION
    content: str | None = None


class HeartbeatMessage(CommunicationMessage):
    """ハートビートメッセージ"""

    type: MessageType = MessageType.HEARTBEAT
    content: str | None = "ping"


# ------------------------------------------------------------
# 状態管理
# ------------------------------------------------------------


class GUIState(BaseModel):
    """GUI状態管理"""

    model_config = ConfigDict(use_enum_values=False)

    status: ConnectionStatus
    connected_device: str | None = None
    error_message: str | None = None
