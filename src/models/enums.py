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
        if system_lower == "windows":
            return cls.WINDOWS
        msg = f"Unsupported platform: {system}"
        raise ValueError(msg)


class RemoteCommand(str, Enum):
    """リモート通信コマンド"""

    END_SESSION = "end_session"


class MessageType(str, Enum):
    """メッセージタイプ"""

    MEET_URL = "meet_url"
    COMMAND = "command"
    HEARTBEAT = "heartbeat"


class ProcessName(str, Enum):
    """プロセス名"""

    CHROME = "chrome"
    CHROME_EXE = "chrome.exe"

    @classmethod
    def get_chrome_process(cls, platform: Platform) -> "ProcessName":
        """プラットフォーム別のChromeプロセス名を取得"""
        if platform == Platform.WINDOWS:
            return cls.CHROME_EXE
        return cls.CHROME
