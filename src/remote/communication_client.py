"""
通信クライアントクラス（リモートPC用）
Tailscaleを使用してフロントPCとの通信を管理する
"""

import contextlib
import json
import logging
import socket
import threading
from datetime import datetime
from typing import Any

from ..utils.tailscale_utils import TailscaleUtils, check_and_setup_tailscale

# ロギング設定
logger = logging.getLogger(__name__)


class CommunicationClient:
    """フロントPCとの通信を管理するクライアント"""

    # 接続プール（簡単な実装）
    _connection_pool = {}
    _pool_lock = threading.Lock()

    def __init__(
        self,
        front_pc_name: str,
        port: int = 9999,
        timeout: int = 10,
        resolve_timeout: int = 15,
    ):
        """
        Args:
            front_pc_name: フロントPCのTailscaleデバイス名（またはIPアドレス）
            port: 通信ポート
            timeout: 接続タイムアウト時間（秒）
            resolve_timeout: デバイス名解決タイムアウト（秒）
        """
        self.front_pc_name = front_pc_name
        self.port = port
        self.timeout = timeout
        self.resolve_timeout = resolve_timeout
        self.socket: socket.socket | None = None
        self.front_pc_ip: str | None = None
        self._pool_key = f"{front_pc_name}:{port}"

    def _get_pooled_connection(self) -> socket.socket | None:
        """プールから利用可能な接続を取得"""
        with CommunicationClient._pool_lock:
            if self._pool_key in CommunicationClient._connection_pool:
                sock = CommunicationClient._connection_pool.pop(self._pool_key)
                # 接続が有効かテスト
                try:
                    sock.send(b"")
                    return sock
                except Exception:
                    with contextlib.suppress(Exception):
                        sock.close()
            return None

    def _return_to_pool(self) -> None:
        """接続をプールに戻す"""
        if self.socket:
            with CommunicationClient._pool_lock:
                CommunicationClient._connection_pool[self._pool_key] = self.socket
            self.socket = None

    def connect(self) -> bool:
        """フロントPCに接続"""
        try:
            # プールから接続を再利用
            self.socket = self._get_pooled_connection()
            if self.socket:
                logger.info("プールから接続を再利用")
                return True

            # Tailscaleセットアップの確認
            logger.info("Tailscale設定を確認中...")
            is_valid, message = check_and_setup_tailscale()
            if not is_valid:
                logger.error(f"Tailscale設定エラー: {message}")
                logger.error("TAILSCALE_SETUP.mdを参照してTailscaleを設定してください")
                return False

            logger.info(f"Tailscale確認完了: {message}")

            # フロントPCのIPアドレスを並列解決
            if self.front_pc_name.replace(".", "").isdigit():
                # IPアドレスが直接指定された場合
                self.front_pc_ip = self.front_pc_name
                logger.info(f"IPアドレス直接指定: {self.front_pc_ip}")
            else:
                # タイムアウト付きでデバイス名解決
                import concurrent.futures

                logger.info(
                    f"デバイス名 '{self.front_pc_name}' を解決中... (タイムアウト: {self.resolve_timeout}秒)"
                )

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    # デバイス名解決
                    resolve_future = executor.submit(
                        TailscaleUtils.resolve_device_name, self.front_pc_name
                    )

                    # 待機中にキャッシュ更新（失敗しても続行）
                    cache_future = executor.submit(TailscaleUtils._get_status_data)

                    try:
                        # タイムアウト付きで結果を待つ
                        self.front_pc_ip = resolve_future.result(
                            timeout=self.resolve_timeout
                        )
                        logger.info(f"デバイス名解決成功: {self.front_pc_ip}")
                    except concurrent.futures.TimeoutError:
                        logger.error(
                            f"デバイス名解決タイムアウト ({self.resolve_timeout}秒)"
                        )
                        logger.error(
                            "Tailscaleの状態を確認し、デバイス名が正しいか確認してください"
                        )
                        return False

                    # キャッシュ更新を待つ（失敗しても続行）
                    with contextlib.suppress(Exception):
                        cache_future.result(timeout=2)

                if not self.front_pc_ip:
                    logger.error(
                        f"フロントPCのデバイス '{self.front_pc_name}' が見つかりません"
                    )

                    # 利用可能なデバイス一覧を表示
                    devices = TailscaleUtils.get_tailscale_devices()
                    if devices:
                        logger.info("利用可能なデバイス:")
                        for hostname, ip in devices.items():
                            logger.info(f"  - {hostname}: {ip}")
                    return False

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            # TCP_NODELAYでレイテンシを減らす
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            logger.info(
                f"フロントPCに接続中: {self.front_pc_ip}:{self.port} (タイムアウト: {self.timeout}秒)"
            )

            # 接続タイムアウトを短く設定
            import time

            start_time = time.time()
            self.socket.connect((self.front_pc_ip, self.port))
            connect_time = time.time() - start_time
            logger.info(f"接続成功 ({connect_time:.2f}秒)")
            return True

        except TimeoutError:
            logger.error(f"接続タイムアウト ({self.timeout}秒)")
            self._cleanup_socket()
            return False
        except ConnectionRefusedError:
            logger.error(
                f"接続拒否: {self.front_pc_ip}:{self.port} (フロントPCのサーバーが起動していない可能性)"
            )
            self._cleanup_socket()
            return False
        except OSError as e:
            if e.errno == 65:  # No route to host
                logger.error(
                    f"ルートが見つかりません: {self.front_pc_ip} (Tailscale接続を確認してください)"
                )
            else:
                logger.error(f"ネットワークエラー: {e}")
            self._cleanup_socket()
            return False
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            self._cleanup_socket()
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
            message_bytes = json_message.encode("utf-8")

            # メッセージ長を送信してからメッセージを送信
            self.socket.sendall(len(message_bytes).to_bytes(4, "big"))
            self.socket.sendall(message_bytes)

            logger.info(
                f"メッセージ送信: {message_data.get('type')} - {message_data.get('content')}"
            )

            # 応答受信はオプショナルに変更（パフォーマンス改善）
            self.socket.settimeout(1)  # 短いタイムアウト
            try:
                response_length = int.from_bytes(self.socket.recv(4), "big")
                if response_length > 0:
                    response = self.socket.recv(response_length)
                    if response:
                        response_data = json.loads(response.decode("utf-8"))
                        logger.info(
                            f"応答受信: {response_data.get('message', 'No message')}"
                        )
                        return response_data.get("status") == "received"
            except TimeoutError:
                # タイムアウトは送信成功とみなす
                pass
            finally:
                self.socket.settimeout(self.timeout)  # 元のタイムアウトに戻す

            return True

        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False

    def is_connected(self) -> bool:
        """接続状態を確認"""
        return self.socket is not None

    def _cleanup_socket(self) -> None:
        """ソケットのクリーンアップ"""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            finally:
                self.socket = None

    def disconnect(self, reuse: bool = True) -> None:
        """接続を切断またはプールに戻す"""
        if self.socket:
            if reuse:
                try:
                    self._return_to_pool()
                    logger.info("接続をプールに戻しました")
                    return
                except Exception as e:
                    logger.error(f"プール返却エラー: {e}")

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
        # 未使用パラメータを明示的に無視
        del exc_type, exc_val, exc_tb
