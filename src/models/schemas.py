"""
Pydantic モデル定義
データの検証と型安全性を確保
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator, ConfigDict

from .enums import ConnectionStatus, MessageType, Platform, RemoteCommand


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


class GUIState(BaseModel):
    """GUI状態管理"""
    model_config = ConfigDict(use_enum_values=True)
    
    status: ConnectionStatus
    connected_device: str | None = None
    error_message: str | None = None


class ConnectionConfig(BaseModel):
    """接続設定"""
    host: str = Field(default="0.0.0.0", description="ホストアドレス")
    port: int = Field(default=9999, ge=1024, le=65535, description="ポート番号")
    display_name: str = Field(default="Reception", description="Meet表示名")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
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
    model_config = ConfigDict(use_enum_values=True)
    
    platform: Platform
    chrome_path: str | None = None
    vtube_studio_path: str | None = None
    profile_directory: str


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


class RemoteSettings(BaseModel):
    """リモートPC設定"""
    last_connected_device: str | None = None
    skip_extension_check: bool = False
    skip_account_check: bool = False
