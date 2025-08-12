"""
通信サーバークラス（フロントPC用）
Tailscaleを使用してリモートPCからのメッセージを受信して処理する
"""

import json
import logging
import socket
import struct
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ..utils.tailscale_utils import TailscaleUtils

# ロギング設定
logger = logging.getLogger(__name__)


class CommunicationServer:
    """リモートPCからの通信を受信するサーバー"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        """
        Args:
            host: バインドするホスト
            port: リスニングポート
        """
        self.host = host
        self.port = port
        self.socket: socket.socket | None = None
        self.running = False
        self.server_thread: threading.Thread | None = None

        # メッセージハンドラー
        self.message_handlers: dict[str, Callable[[dict[str, Any]], None]] = {}

        # クライアント接続管理
        self.clients: set[tuple[socket.socket, tuple]] = set()
        self._clients_lock = threading.Lock()

    def register_handler(
        self, message_type: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """メッセージタイプに対するハンドラーを登録"""
        self.message_handlers[message_type] = handler
        logger.info(f"ハンドラー登録: {message_type}")

    def start_server(self) -> bool:
        """サーバーを開始"""
        try:
            # Tailscaleセットアップの確認
            is_valid, message = TailscaleUtils.check_and_setup_tailscale()
            if not is_valid:
                logger.error(f"Tailscale設定エラー: {message}")
                logger.error("TAILSCALE_SETUP.mdを参照してTailscaleを設定してください")
                return False

            logger.info(f"Tailscale確認完了: {message}")

            # 自分のTailscale IPアドレスを表示
            my_ip = TailscaleUtils.get_my_tailscale_ip()
            if my_ip:
                logger.info(f"このデバイスのTailscale IP: {my_ip}")
                logger.info("=== Tailscale情報 ===")
                logger.info(f"このデバイスのIP: {my_ip}")

                # 利用可能なデバイス一覧を表示
                devices = TailscaleUtils.get_tailscale_devices()
                if devices:
                    logger.info("利用可能なデバイス:")
                    for hostname, ip in devices.items():
                        logger.info(f"  - {hostname}: {ip}")
                logger.info("=" * 20)

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)

            self.running = True
            logger.info(f"サーバー開始: {self.host}:{self.port}")

            # 別スレッドでサーバー実行
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            return True

        except Exception as e:
            logger.error(f"サーバー開始エラー: {e}")
            return False

    def _run_server(self) -> None:
        """サーバーメインループ"""
        logger.info("リモートPCからの接続を待機中...")

        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                logger.info(f"接続受付: {client_address}")

                # クライアント処理を別スレッドで実行
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                )
                client_thread.start()

            except Exception as e:
                if self.running:
                    logger.error(f"接続受付エラー: {e}")

    def _handle_client(
        self, client_socket: socket.socket, client_address: tuple
    ) -> None:
        """クライアント接続処理（長さプレフィックス対応）"""
        # クライアント接続をリストに追加
        with self._clients_lock:
            self.clients.add((client_socket, client_address))
        logger.info(
            f"クライアント接続追加: {client_address} (総数: {len(self.clients)})"
        )

        try:
            client_socket.settimeout(30)  # 30秒タイムアウト

            while True:
                # メッセージ長を受信（4バイト）
                try:
                    length_bytes = self._recv_exact(client_socket, 4)
                    if not length_bytes:
                        break

                    message_length = int.from_bytes(length_bytes, "big")
                    if message_length > 10 * 1024 * 1024:  # 10MB以上はエラー
                        logger.error(
                            f"メッセージが大きすぎます: {message_length}バイト"
                        )
                        break

                    # 実際のメッセージを受信
                    message_bytes = self._recv_exact(client_socket, message_length)
                    if not message_bytes:
                        break

                    message = message_bytes.decode("utf-8")
                    logger.info(
                        f"メッセージ受信 from {client_address}: {message[:100]}..."
                    )

                    # JSONメッセージとして処理
                    try:
                        json_data = json.loads(message)
                        self._process_message(json_data)

                        # 受信確認を長さプレフィックス付きで送信
                        response_data = {
                            "status": "received",
                            "timestamp": datetime.now().isoformat(),
                            "message": "メッセージを受信しました",
                        }
                        response = json.dumps(response_data).encode("utf-8")

                        # 長さプレフィックス付きで送信
                        client_socket.sendall(len(response).to_bytes(4, "big"))
                        client_socket.sendall(response)

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失敗 from {client_address}: {e}")
                        logger.error(f"受信メッセージ: {message[:200]}")

                except UnicodeDecodeError as e:
                    logger.error(f"メッセージデコードエラー from {client_address}: {e}")
                    break
                except TimeoutError:
                    logger.warning(f"クライアントタイムアウト: {client_address}")
                    break
                except struct.error as e:
                    logger.error(f"メッセージ長解析エラー from {client_address}: {e}")
                    break

        except ConnectionResetError:
            logger.info(f"クライアント切断: {client_address}")
        except Exception as e:
            logger.error(f"クライアント処理エラー from {client_address}: {e}")
        finally:
            # クライアント接続をリストから削除
            with self._clients_lock:
                self.clients.discard((client_socket, client_address))
            logger.info(
                f"クライアント接続終了: {client_address} (残り: {len(self.clients)})"
            )
            client_socket.close()

    def _process_message(self, data: dict[str, Any]) -> None:
        """受信メッセージを処理"""
        message_type = data.get("type", "unknown")
        logger.info(f"メッセージ処理: {message_type}")

        # 登録されたハンドラーで処理
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type](data)
            except Exception as e:
                logger.error(f"ハンドラー実行エラー ({message_type}): {e}")
        else:
            logger.warning(f"未知のメッセージタイプ: {message_type}")
            self._default_message_handler(data)

    def _default_message_handler(self, data: dict[str, Any]) -> None:
        """デフォルトメッセージハンドラー"""
        logger.info("デフォルト処理:")
        logger.info(f"  タイプ: {data.get('type', 'unknown')}")
        logger.info(f"  内容: {data.get('content', '')}")
        logger.info(f"  送信時刻: {data.get('timestamp', 'unknown')}")

    def stop_server(self) -> None:
        """サーバーを停止"""
        logger.info("サーバー停止中...")
        self.running = False

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"ソケット終了エラー: {e}")

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)

        logger.info("サーバーを停止しました")

    def _recv_exact(self, sock: socket.socket, length: int) -> bytes:
        """指定したバイト数を確実に受信"""
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return b""  # 接続が閉じられた
            data += chunk
        return data

    def is_running(self) -> bool:
        """サーバーが動作中かを確認"""
        return self.running

    def __enter__(self) -> "CommunicationServer":
        """コンテキストマネージャーのエントリ"""
        self.start_server()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """コンテキストマネージャーの終了処理"""
        self.stop_server()
        # 未使用パラメータを明示的に無視
        del exc_type, exc_val, exc_tb
