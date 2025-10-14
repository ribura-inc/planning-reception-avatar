"""リモート側で使用する最小構成のTCPクライアント。"""

from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

from src.models.enums import MessageType
from src.utils.tailscale_utils import TailscaleUtils

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClientConfig:
    """クライアント接続設定。"""

    host: str
    port: int = 9999
    timeout: float = 10.0


class CommunicationClient:
    """長さプレフィックス付きTCP通信を扱う軽量ラッパー。"""

    def __init__(self, host_or_device: str, port: int = 9999, timeout: float = 10.0) -> None:
        resolved = TailscaleUtils.resolve_device_name(host_or_device) or host_or_device
        self.config = ClientConfig(host=resolved, port=port, timeout=timeout)
        self._socket: socket.socket | None = None

    # ------------------------------------------------------------------
    # 接続系ヘルパー
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        if self._socket:
            return True

        try:
            sock = socket.create_connection(
                (self.config.host, self.config.port),
                timeout=self.config.timeout,
            )
            sock.settimeout(self.config.timeout)
            self._socket = sock
            return True  # noqa: TRY300
        except OSError:
            logger.exception("フロントPCへの接続に失敗しました")
            self._socket = None
            return False

    def disconnect(self) -> None:
        if not self._socket:
            return
        try:
            self._socket.close()
        except OSError as exc:
            logger.warning("ソケット切断エラー: %s", exc)
        finally:
            self._socket = None

    # ------------------------------------------------------------------
    # メッセージ送信
    # ------------------------------------------------------------------
    def send_meet_url(self, meet_url: str) -> bool:
        payload = {
            "type": MessageType.MEET_URL.value,
            "content": meet_url,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return self._send(payload)

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> bool:
        payload = {
            "type": MessageType.COMMAND.value,
            "content": command,
            "timestamp": datetime.now(UTC).isoformat(),
            "params": params or {},
        }
        return self._send(payload)

    def _send(self, payload: dict[str, Any]) -> bool:
        if not self._socket:
            logger.error("ソケットが未接続です")
            return False

        message = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        length_prefix = len(message).to_bytes(4, "big")

        try:
            self._socket.sendall(length_prefix + message)
            response_length_bytes = self._socket.recv(4)
            if not response_length_bytes:
                return False
            response_length = int.from_bytes(response_length_bytes, "big")
            if response_length == 0:
                return True
            response = self._socket.recv(response_length)
            if not response:
                return False
            data = json.loads(response.decode("utf-8"))
            return data.get("status") == "received"
        except OSError:
            logger.exception("メッセージ送信エラー")
            return False

    # ------------------------------------------------------------------
    # コンテキストマネージャーヘルパー
    # ------------------------------------------------------------------
    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        self.disconnect()
