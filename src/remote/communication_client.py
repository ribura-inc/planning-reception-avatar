"""リモート側で使用する最小構成のTCPクライアント。"""

from __future__ import annotations

import json
import logging
import socket
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Self

from src.config import Config
from src.models.enums import MessageType
from src.utils.slack import SessionLocation, notify_error
from src.utils.tailscale_utils import TailscaleUtils

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class CommunicationClient:
    """長さプレフィックス付きTCP通信を扱う軽量ラッパー。"""

    def __init__(
        self,
        host_or_device: str,
        port: int = Config.Communication.PORT,
        timeout: float = Config.Communication.TIMEOUT,
    ) -> None:
        resolved = TailscaleUtils.resolve_device_name(host_or_device) or host_or_device
        self.host = resolved
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop_event: threading.Event = threading.Event()
        self._on_connection_lost: Callable[[], None] | None = None

    def set_connection_lost_callback(self, callback: Callable[[], None]) -> None:
        """接続喪失時に呼び出されるコールバックを設定

        Args:
            callback: 接続が失われた際に呼び出される関数
        """
        self._on_connection_lost = callback

    # ------------------------------------------------------------------
    # 接続系ヘルパー
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        if self._socket:
            return True

        try:
            sock = socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout,
            )
            sock.settimeout(self.timeout)
            self._socket = sock
            self._start_heartbeat()  # ハートビート開始
            return True  # noqa: TRY300
        except OSError as e:
            logger.exception("フロントPCへの接続に失敗しました")
            notify_error(
                error=e,
                context="フロントPCへの接続失敗",
                additional_info={
                    "ホスト": self.host,
                    "ポート": str(self.port),
                },
                location=SessionLocation.REMOTE,
            )
            self._socket = None
            return False

    def _start_heartbeat(self) -> None:
        """ハートビート送信スレッドを開始。"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
        )
        self._heartbeat_thread.start()
        logger.info("ハートビート送信開始")

    def _heartbeat_loop(self) -> None:
        """定期的にハートビートを送信し、失敗時はリトライする。"""
        consecutive_failures = 0

        while not self._heartbeat_stop_event.wait(timeout=Config.Communication.HEARTBEAT_INTERVAL):
            if not self._socket:
                break

            try:
                payload = {
                    "type": MessageType.HEARTBEAT.value,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                message = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                length_prefix = len(message).to_bytes(4, "big")
                self._socket.sendall(length_prefix + message)

                # 応答を受信（ブロッキング）
                response_length_bytes = self._socket.recv(4)
                if response_length_bytes:
                    response_length = int.from_bytes(response_length_bytes, "big")
                    if response_length > 0:
                        self._socket.recv(response_length)

                # 成功時はカウンタリセット
                consecutive_failures = 0
                logger.debug("ハートビート送信成功")

            except OSError:
                consecutive_failures += 1
                logger.warning(
                    "ハートビート送信失敗 (%d/%d)",
                    consecutive_failures,
                    Config.Communication.HEARTBEAT_MAX_FAILURES,
                    exc_info=True,
                )

                # 最大失敗回数に達したら接続を切断
                if consecutive_failures >= Config.Communication.HEARTBEAT_MAX_FAILURES:
                    logger.error(  # noqa: TRY400
                        "ハートビート連続失敗により接続を切断します (失敗回数: %d)",
                        consecutive_failures,
                    )
                    # Slack通知を送信
                    notify_error(
                        error=Exception("ハートビート連続失敗"),
                        context="フロントPCとの接続維持失敗",
                        additional_info={
                            "失敗回数": f"{consecutive_failures}回",
                            "最大失敗回数": f"{Config.Communication.HEARTBEAT_MAX_FAILURES}回",
                            "ホスト": self.host,
                        },
                        location=SessionLocation.REMOTE,
                    )
                    self._force_disconnect()
                    # 接続喪失コールバックを呼び出す
                    if self._on_connection_lost:
                        try:
                            self._on_connection_lost()
                        except Exception:
                            logger.exception("接続喪失コールバック実行エラー")
                    break

    def _stop_heartbeat(self) -> None:
        """ハートビート送信スレッドを停止。"""
        if not self._heartbeat_thread:
            return

        self._heartbeat_stop_event.set()
        self._heartbeat_thread.join(timeout=2.0)
        self._heartbeat_thread = None
        logger.info("ハートビート送信停止")

    def _force_disconnect(self) -> None:
        """ソケットを強制的にクローズ（ハートビートスレッドから呼び出される）。"""
        if not self._socket:
            return
        try:
            self._socket.close()
        except OSError as exc:
            logger.warning("ソケット強制切断エラー: %s", exc)
        finally:
            self._socket = None
            logger.info("接続を強制切断しました")

    def disconnect(self) -> None:
        if not self._socket:
            return
        self._stop_heartbeat()  # ハートビート停止
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
