"""
通信クライアントクラス（リモートPC用）
Tailscaleを使用してフロントPCとの通信を管理する
"""

import contextlib
import json
import logging
import socket
import threading
import time
from datetime import datetime
from typing import Any

from ..models.enums import MessageType
from ..utils.tailscale_utils import TailscaleUtils, check_and_setup_tailscale

# ロギング設定
logger = logging.getLogger(__name__)


class CommunicationClient:
    """フロントPCとの通信を管理するクライアント"""

    # クラス変数（全インスタンス共有）
    _connection_pool = {}
    _pool_lock = threading.Lock()
    _tailscale_verified = False
    _tailscale_check_time = 0
    _device_cache = {}  # デバイス名からIPへのキャッシュ
    _cache_lock = threading.Lock()
    TAILSCALE_CHECK_INTERVAL = 300  # 5分間はTailscale確認をスキップ

    def __init__(
        self,
        front_pc_name: str,
        port: int = 9999,
        timeout: int = 10,
        resolve_timeout: int = 5,  # デフォルトを短縮
        pre_connect: bool = True,  # 事前接続を有効化
    ):
        """
        Args:
            front_pc_name: フロントPCのTailscaleデバイス名（またはIPアドレス）
            port: 通信ポート
            timeout: 接続タイムアウト時間（秒）
            resolve_timeout: デバイス名解決タイムアウト（秒）
            pre_connect: 初期化時に事前接続を行うか
        """
        self.front_pc_name = front_pc_name
        self.port = port
        self.timeout = timeout
        self.resolve_timeout = resolve_timeout
        self.socket: socket.socket | None = None
        self.front_pc_ip: str | None = None
        self._pool_key = f"{front_pc_name}:{port}"

        # 事前接続を非同期で実行
        if pre_connect:
            self._start_preconnect()

    def _start_preconnect(self):
        """非同期で事前接続を開始"""
        thread = threading.Thread(target=self._preconnect, daemon=True)
        thread.start()

    def _preconnect(self):
        """バックグラウンドで事前接続を実行"""
        try:
            # IPアドレスを事前解決
            if not self.front_pc_name.replace(".", "").isdigit():
                self._resolve_device_name_cached()

            # 接続プールに事前接続を作成
            temp_client = CommunicationClient(
                self.front_pc_name, self.port, pre_connect=False
            )
            if temp_client._quick_connect():
                temp_client._return_to_pool()
                logger.info("事前接続をプールに追加しました")
        except Exception as e:
            logger.debug(f"事前接続エラー（無視）: {e}")

    def _resolve_device_name_cached(self) -> str | None:
        """キャッシュを使用してデバイス名を解決"""
        with self._cache_lock:
            if self.front_pc_name in self._device_cache:
                cached_ip = self._device_cache[self.front_pc_name]
                logger.info(
                    f"キャッシュからIP取得: {self.front_pc_name} -> {cached_ip}"
                )
                return cached_ip

        # キャッシュにない場合は解決
        ip = TailscaleUtils.resolve_device_name(self.front_pc_name)
        if ip:
            with self._cache_lock:
                self._device_cache[self.front_pc_name] = ip
            logger.info(f"デバイス名解決: {self.front_pc_name} -> {ip}")

        return ip

    def _verify_tailscale_once(self) -> bool:
        """Tailscaleの確認を一度だけ実行（キャッシュ利用）"""
        current_time = time.time()

        if (
            self._tailscale_verified
            and current_time - self._tailscale_check_time
            < self.TAILSCALE_CHECK_INTERVAL
        ):
            return True

        logger.info("Tailscale設定を確認中...")
        is_valid, message = check_and_setup_tailscale()
        if is_valid:
            CommunicationClient._tailscale_verified = True
            CommunicationClient._tailscale_check_time = current_time
            logger.info(f"Tailscale確認完了: {message}")
        else:
            logger.error(f"Tailscale設定エラー: {message}")

        return is_valid

    def _get_pooled_connection(self) -> socket.socket | None:
        """プールから利用可能な接続を取得"""
        with self._pool_lock:
            if self._pool_key in self._connection_pool:
                sock = self._connection_pool.pop(self._pool_key)
                # 接続が有効かテスト（高速化のため最小限のチェック）
                try:
                    # ソケットの状態を確認
                    sock.setblocking(False)
                    with contextlib.suppress(BlockingIOError):
                        # 0バイト送信で接続状態を確認
                        sock.send(b"")
                    sock.setblocking(True)
                    return sock
                except Exception:
                    with contextlib.suppress(Exception):
                        sock.close()
            return None

    def _return_to_pool(self) -> None:
        """接続をプールに戻す"""
        if self.socket:
            with self._pool_lock:
                self._connection_pool[self._pool_key] = self.socket
            self.socket = None

    def _quick_connect(self) -> bool:
        """高速接続（最小限のチェック）"""
        try:
            # IPアドレスの解決
            if self.front_pc_name.replace(".", "").isdigit():
                self.front_pc_ip = self.front_pc_name
            else:
                self.front_pc_ip = self._resolve_device_name_cached()
                if not self.front_pc_ip:
                    return False

            # ソケット作成と接続
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # SO_KEEPALIVE を設定して接続の健全性を保つ
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            self.socket.connect((self.front_pc_ip, self.port))
            return True

        except Exception as e:
            logger.error(f"接続エラー: {e}")
            self._cleanup_socket()
            return False

    def connect(self) -> bool:
        """フロントPCに接続（最適化版）"""
        try:
            # プールから接続を再利用
            self.socket = self._get_pooled_connection()
            if self.socket:
                logger.info("プールから接続を再利用")
                return True

            # Tailscale確認（キャッシュ利用）
            if not self._verify_tailscale_once():
                return False

            # 高速接続
            start_time = time.time()
            success = self._quick_connect()
            if success:
                connect_time = time.time() - start_time
                logger.info(f"接続成功 ({connect_time:.3f}秒)")

            return success

        except Exception as e:
            logger.error(f"接続エラー: {e}")
            self._cleanup_socket()
            return False

    def send_meet_url(self, meet_url: str) -> bool:
        """Meet URLをフロントPCに送信"""
        message_data = {
            "type": MessageType.MEET_URL.value,
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
        """JSON形式でメッセージを送信（最適化版）"""
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

            # 応答受信を非同期化（ブロックしない）
            self.socket.settimeout(0.1)  # より短いタイムアウト
            try:
                response_length = int.from_bytes(self.socket.recv(4), "big")
                if response_length > 0:
                    response = self.socket.recv(response_length)
                    if response:
                        response_data = json.loads(response.decode("utf-8"))
                        return response_data.get("status") == "received"
            except (TimeoutError, BlockingIOError):
                # タイムアウトまたは非ブロッキングエラーは成功とみなす
                pass
            finally:
                self.socket.settimeout(self.timeout)

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

    def send_heartbeat(self) -> bool:
        """ハートビート信号を送信して接続を維持"""
        return self.send_notification(MessageType.HEARTBEAT.value)

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
        del exc_type, exc_val, exc_tb

    @classmethod
    def clear_cache(cls):
        """キャッシュをクリア"""
        with cls._cache_lock:
            cls._device_cache.clear()
        cls._tailscale_verified = False
        cls._tailscale_check_time = 0
        logger.info("キャッシュをクリアしました")

    @classmethod
    def preload_devices(cls, device_names: list[str]):
        """デバイス名を事前に解決してキャッシュ"""
        logger.info(f"{len(device_names)}個のデバイスを事前解決中...")

        for name in device_names:
            if name.replace(".", "").isdigit():
                continue  # IPアドレスはスキップ

            ip = TailscaleUtils.resolve_device_name(name)
            if ip:
                with cls._cache_lock:
                    cls._device_cache[name] = ip
                logger.info(f"事前解決: {name} -> {ip}")
