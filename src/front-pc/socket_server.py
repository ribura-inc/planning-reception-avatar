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


class FrontPCSocketServer:
    """フロントPC用ソケットサーバー

    リモートPCからのメッセージを受信し、ログ出力する
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        """サーバー初期化

        Args:
            host: バインドするホスト（0.0.0.0で全インターフェース）
            port: リスニングポート
        """
        self.host = host
        self.port = port
        self.socket = None

    def start_server(self) -> None:
        """サーバー開始"""
        try:
            # ソケット作成
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # バインドとリスニング開始
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)

            logger.info(f"サーバー開始: {self.host}:{self.port}")
            logger.info("リモートPCからの接続を待機中...")

            while True:
                try:
                    # クライアント接続受付
                    client_socket, client_address = self.socket.accept()
                    logger.info(f"接続受付: {client_address}")

                    # メッセージ受信処理
                    self._handle_client(client_socket, client_address)

                except KeyboardInterrupt:
                    logger.info("サーバー停止要求を受信")
                    break
                except Exception as e:
                    logger.error(f"クライアント処理エラー: {e}")

        except Exception as e:
            logger.error(f"サーバー開始エラー: {e}")
        finally:
            self._cleanup()

    def _handle_client(
        self, client_socket: socket.socket, client_address: tuple
    ) -> None:
        """クライアント接続処理

        Args:
            client_socket: クライアントソケット
            client_address: クライアントアドレス
        """
        try:
            while True:
                # データ受信（最大4096バイト）
                data = client_socket.recv(4096)
                if not data:
                    break

                # メッセージデコード
                try:
                    message = data.decode("utf-8")
                    logger.info(f"メッセージ受信 from {client_address}: {message}")

                    # JSON形式の場合はパース
                    try:
                        json_data = json.loads(message)
                        self._process_json_message(json_data, client_address)
                    except json.JSONDecodeError:
                        # 普通のテキストメッセージとして処理
                        self._process_text_message(message, client_address)

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

    def _process_json_message(
        self, data: dict[str, Any], client_address: tuple
    ) -> None:
        """JSON形式メッセージ処理

        Args:
            data: JSONデータ
            client_address: クライアントアドレス
        """
        logger.info(f"JSON メッセージ from {client_address}:")
        logger.info(f"  タイプ: {data.get('type', 'unknown')}")
        logger.info(f"  内容: {data.get('content', '')}")
        logger.info(f"  送信時刻: {data.get('timestamp', 'unknown')}")

    def _process_text_message(self, message: str, client_address: tuple) -> None:
        """テキストメッセージ処理

        Args:
            message: テキストメッセージ
            client_address: クライアントアドレス
        """
        logger.info(f"テキスト メッセージ from {client_address}: {message}")

    def _cleanup(self) -> None:
        """リソースクリーンアップ"""
        if self.socket:
            self.socket.close()
            logger.info("サーバーソケットを閉じました")


def main():
    """メイン関数"""
    server = FrontPCSocketServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("プログラム終了")


if __name__ == "__main__":
    main()
