"""
通信サーバークラス（フロントPC用）
リモートPCからのメッセージを受信して処理する
"""

import json
import logging
import socket
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any

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

    def register_handler(
        self, message_type: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """メッセージタイプに対するハンドラーを登録"""
        self.message_handlers[message_type] = handler
        logger.info(f"ハンドラー登録: {message_type}")

    def start_server(self) -> bool:
        """サーバーを開始"""
        try:
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
        """クライアント接続処理"""
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message = data.decode("utf-8")
                    logger.info(f"メッセージ受信 from {client_address}: {message}")

                    # JSONメッセージとして処理
                    try:
                        json_data = json.loads(message)
                        self._process_message(json_data)
                    except json.JSONDecodeError:
                        logger.warning(f"JSON解析失敗: {message}")

                    # 受信確認を送信
                    response = json.dumps(
                        {
                            "status": "received",
                            "timestamp": datetime.now().isoformat(),
                            "message": "メッセージを受信しました",
                        }
                    ).encode("utf-8")
                    client_socket.send(response)

                except UnicodeDecodeError:
                    logger.error(f"メッセージデコードエラー from {client_address}")

        except ConnectionResetError:
            logger.info(f"クライアント切断: {client_address}")
        except Exception as e:
            logger.error(f"クライアント処理エラー: {e}")
        finally:
            client_socket.close()
            logger.info(f"クライアント接続終了: {client_address}")

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
