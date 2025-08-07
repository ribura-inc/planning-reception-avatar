"""
共通Enum定義
文字列リテラルの曖昧性を排除し、型安全性を向上
"""

from enum import Enum


class Platform(str, Enum):
    """プラットフォーム定義"""

    WINDOWS = "windows"
    MACOS = "macos"

    @classmethod
    def from_system(cls, system: str) -> "Platform":
        """システム名からPlatformを取得"""
        system_lower = system.lower()
        if system_lower == "darwin":
            return cls.MACOS
        elif system_lower == "windows":
            return cls.WINDOWS
        else:
            raise ValueError(f"Unsupported platform: {system}")


class ConnectionStatus(str, Enum):
    """接続状態"""

    # フロントPC用
    WAITING = "待機中"
    CONNECTING = "接続中"
    CONNECTED = "接続済み"
    DISCONNECTING = "切断中"
    ERROR = "エラー"

    # リモートPC用
    NOT_CONNECTED = "未接続"
    IN_SESSION = "セッション中"


class RemoteCommand(str, Enum):
    """リモート通信コマンド"""

    END_SESSION = "end_session"
    LEAVE_MEETING = "leave_meeting"
    JOIN_MEETING = "join_meeting"
    FORCE_CLEANUP = "force_cleanup"


class MessageType(str, Enum):
    """メッセージタイプ"""

    MEET_URL = "meet_url"
    COMMAND = "command"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"


class ProcessName(str, Enum):
    """プロセス名"""

    CHROME = "chrome"
    CHROME_EXE = "chrome.exe"
    VTUBE_STUDIO = "VTube Studio"
    VTUBE_STUDIO_EXE = "VTube Studio.exe"

    @classmethod
    def get_chrome_process(cls, platform: Platform) -> "ProcessName":
        """プラットフォーム別のChromeプロセス名を取得"""
        if platform == Platform.WINDOWS:
            return cls.CHROME_EXE
        return cls.CHROME
