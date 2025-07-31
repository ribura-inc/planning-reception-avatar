"""
Pydantic モデル定義
データの検証と型安全性を確保
"""

from typing import Any

from pydantic import BaseModel, Field, validator

from .enums import ConnectionStatus, MessageType, Platform, RemoteCommand


class CommunicationMessage(BaseModel):
    """通信メッセージの基本構造"""
    type: MessageType
    content: str | None = None
    params: dict[str, Any] | None = None

    class Config:
        use_enum_values = True


class MeetURLMessage(CommunicationMessage):
    """Meet URL送信メッセージ"""
    type: MessageType = MessageType.MEET_URL
    content: str = Field(..., description="Google Meet URL")

    @validator("content")
    def validate_meet_url(cls, v: str) -> str:  # noqa: N805
        """Meet URLの妥当性を検証"""
        if not v.startswith("https://meet.google.com/"):
            raise ValueError("Invalid Meet URL format")
        return v


class CommandMessage(CommunicationMessage):
    """コマンドメッセージ"""
    type: MessageType = MessageType.COMMAND
    content: RemoteCommand

    class Config:
        use_enum_values = True


class NotificationMessage(CommunicationMessage):
    """通知メッセージ"""
    type: MessageType = MessageType.NOTIFICATION
    content: str


class HeartbeatMessage(CommunicationMessage):
    """ハートビートメッセージ"""
    type: MessageType = MessageType.HEARTBEAT
    content: str = "ping"


class GUIState(BaseModel):
    """GUI状態管理"""
    status: ConnectionStatus
    connected_device: str | None = None
    error_message: str | None = None

    class Config:
        use_enum_values = True


class ConnectionConfig(BaseModel):
    """接続設定"""
    host: str = Field(default="0.0.0.0", description="ホストアドレス")
    port: int = Field(default=9999, ge=1024, le=65535, description="ポート番号")
    display_name: str = Field(default="Reception", description="Meet表示名")

    @validator("host")
    def validate_host(cls, v: str) -> str:  # noqa: N805
        """ホストアドレスの検証"""
        if not v:
            raise ValueError("Host cannot be empty")
        return v


class SessionConfig(BaseModel):
    """セッション設定"""
    front_pc_address: str = Field(..., description="フロントPCのアドレスまたはTailscale名")
    skip_extension_check: bool = Field(default=False, description="拡張機能チェックをスキップ")
    skip_account_check: bool = Field(default=False, description="Googleアカウントチェックをスキップ")


class ApplicationConfig(BaseModel):
    """アプリケーション設定"""
    platform: Platform
    chrome_path: str | None = None
    vtube_studio_path: str | None = None
    profile_directory: str

    class Config:
        use_enum_values = True


class VTubeStudioStatus(BaseModel):
    """VTube Studio状態"""
    is_running: bool
    message: str
    launch_attempted: bool = False


class ChromeProcessInfo(BaseModel):
    """Chromeプロセス情報"""
    pid: int | None = None
    is_running: bool = False
    current_url: str | None = None
