"""
通信クライアントクラス（リモートPC用）
フロントPCとの通信を管理する
"""

import json
import logging
import socket
from datetime import datetime
from typing import Any

# ロギング設定
logger = logging.getLogger(__name__)


class CommunicationClient:
    """フロントPCとの通信を管理するクライアント"""

    def __init__(self, front_pc_ip: str, port: int = 9999, timeout: int = 10):
        """
        Args:
            front_pc_ip: フロントPCのIPアドレス
            port: 通信ポート
            timeout: 接続タイムアウト時間（秒）
        """
        self.front_pc_ip = front_pc_ip
        self.port = port
        self.timeout = timeout
        self.socket: socket.socket | None = None

    def connect(self) -> bool:
        """フロントPCに接続"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)

            logger.info(f"フロントPCに接続中: {self.front_pc_ip}:{self.port}")
            self.socket.connect((self.front_pc_ip, self.port))
            logger.info("接続成功")
            return True

        except TimeoutError:
            logger.error("接続タイムアウト")
            return False
        except ConnectionRefusedError:
            logger.error("接続拒否（フロントPCのサーバーが起動していない可能性）")
            return False
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            return False

    def send_meet_url(self, meet_url: str) -> bool:
        """Meet URLをフロントPCに送信"""
        message_data = {
            "type": "meet_url",
            "content": meet_url,
            "timestamp": datetime.now().isoformat(),
            "action": "join_meeting",
        }

        return self._send_json_message(message_data)

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> bool:
        """コマンドをフロントPCに送信"""
        message_data = {
            "type": "command",
            "content": command,
            "timestamp": datetime.now().isoformat(),
            "params": params or {},
        }

        return self._send_json_message(message_data)

    def send_notification(self, message: str) -> bool:
        """通知メッセージをフロントPCに送信"""
        message_data = {
            "type": "notification",
            "content": message,
            "timestamp": datetime.now().isoformat(),
        }

        return self._send_json_message(message_data)

    def _send_json_message(self, message_data: dict[str, Any]) -> bool:
        """JSON形式でメッセージを送信"""
        if not self.socket:
            logger.error("ソケットが接続されていません")
            return False

        try:
            json_message = json.dumps(message_data, ensure_ascii=False)
            self.socket.send(json_message.encode("utf-8"))
            logger.info(
                f"メッセージ送信: {message_data.get('type')} - {message_data.get('content')}"
            )

            # 応答受信
            response = self.socket.recv(1024)
            if response:
                response_data = json.loads(response.decode("utf-8"))
                logger.info(f"応答受信: {response_data.get('message', 'No message')}")
                return response_data.get("status") == "received"

            return True

        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False

    def is_connected(self) -> bool:
        """接続状態を確認"""
        return self.socket is not None

    def disconnect(self) -> None:
        """接続を切断"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"ソケット切断エラー: {e}")
            finally:
                self.socket = None
                logger.info("接続を切断しました")

    def __enter__(self):
        """コンテキストマネージャーのエントリ"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.disconnect()
