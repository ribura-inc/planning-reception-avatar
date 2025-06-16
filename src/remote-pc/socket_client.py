import json
import logging
import socket
from datetime import datetime
from typing import Any

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RemotePCSocketClient:
    """リモートPC用ソケットクライアント

    フロントPCへメッセージを送信する
    """

    def __init__(self, front_pc_ip: str, port: int = 9999):
        """クライアント初期化

        Args:
            front_pc_ip: フロントPCのグローバルIP
            port: 接続ポート
        """
        self.front_pc_ip = front_pc_ip
        self.port = port
        self.socket = None

    def connect(self) -> bool:
        """フロントPCに接続

        Returns:
            接続成功: True, 接続失敗: False
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10秒タイムアウト

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

    def send_text_message(self, message: str) -> bool:
        """テキストメッセージ送信

        Args:
            message: 送信するメッセージ

        Returns:
            送信成功: True, 送信失敗: False
        """
        if not self.socket:
            logger.error("ソケットが接続されていません")
            return False

        try:
            # メッセージをUTF-8でエンコードして送信
            self.socket.send(message.encode("utf-8"))
            logger.info(f"テキストメッセージ送信: {message}")

            # 応答受信
            response = self.socket.recv(1024)
            if response:
                response_data = json.loads(response.decode("utf-8"))
                logger.info(f"応答受信: {response_data.get('message', 'No message')}")

            return True

        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False

    def send_json_message(self, message_type: str, content: str, **kwargs) -> bool:
        """JSON形式メッセージ送信

        Args:
            message_type: メッセージタイプ
            content: メッセージ内容
            **kwargs: 追加データ

        Returns:
            送信成功: True, 送信失敗: False
        """
        if not self.socket:
            logger.error("ソケットが接続されていません")
            return False

        try:
            # JSON形式でメッセージ作成
            message_data = {
                "type": message_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }

            json_message = json.dumps(message_data, ensure_ascii=False)
            self.socket.send(json_message.encode("utf-8"))
            logger.info(f"JSONメッセージ送信: {message_type} - {content}")

            # 応答受信
            response = self.socket.recv(1024)
            if response:
                response_data = json.loads(response.decode("utf-8"))
                logger.info(f"応答受信: {response_data.get('message', 'No message')}")

            return True

        except Exception as e:
            logger.error(f"JSONメッセージ送信エラー: {e}")
            return False

    def disconnect(self) -> None:
        """接続切断"""
        if self.socket:
            self.socket.close()
            self.socket = None
            logger.info("接続を切断しました")

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> bool:
        """コマンド送信（将来の拡張用）

        Args:
            command: コマンド名
            params: コマンドパラメータ

        Returns:
            送信成功: True, 送信失敗: False
        """
        return self.send_json_message(
            message_type="command", content=command, params=params or {}
        )


def main():
    """メイン関数 - 対話式メッセージ送信"""
    # フロントPCのIPアドレスを設定（実際の環境に合わせて変更）
    FRONT_PC_IP = "192.168.1.100"  # 実際のフロントPCのグローバルIPに変更

    client = RemotePCSocketClient(FRONT_PC_IP)

    try:
        # 接続
        if not client.connect():
            logger.error("フロントPCに接続できませんでした")
            return

        print("=== リモートPC → フロントPC メッセージ送信 ===")
        print("メッセージを入力してください (終了: 'quit')")
        print("JSON形式で送信: 'json:タイプ:内容'")
        print("例: json:notification:受付呼び出し")

        while True:
            try:
                message = input("> ")

                if message.lower() == "quit":
                    break

                if message.startswith("json:"):
                    # JSON形式送信
                    parts = message[5:].split(":", 2)
                    if len(parts) >= 2:
                        msg_type = parts[0]
                        content = parts[1] if len(parts) > 1 else ""
                        client.send_json_message(msg_type, content)
                    else:
                        print("JSON形式: json:タイプ:内容")
                else:
                    # テキスト送信
                    client.send_text_message(message)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"入力処理エラー: {e}")

    finally:
        client.disconnect()
        print("プログラムを終了します")


if __name__ == "__main__":
    main()
