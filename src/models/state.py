from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppStatus(str, Enum):
    """UIで共有する主要なアプリケーション状態。"""

    IDLE = "待機中"
    CHECKING = "確認中"
    CONNECTING = "接続準備中"
    CONNECTED = "接続中"
    DISCONNECTING = "切断中"
    ERROR = "エラー"
    SHUTTING_DOWN = "終了処理中"


class NetworkCondition(str, Enum):
    """ネットワーク診断の判定結果。"""

    OK = "正常"
    NO_INTERNET = "インターネット未接続"
    TAILSCALE_UNAVAILABLE = "Tailscale未起動"
    UNKNOWN_ERROR = "不明なエラー"


@dataclass(slots=True)
class StatusMessage:
    """UIコンポーネント更新に用いるメッセージ。"""

    status: AppStatus
    headline: str
    detail: str | None = None


@dataclass(slots=True)
class NetworkCheckResult:
    """ネットワーク診断の結果。"""

    condition: NetworkCondition
    message: str
    tailscale_devices: dict[str, str]
    tailscale_self: str | None
