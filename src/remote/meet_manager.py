"""
Google Meet管理クラス（リモートPC用）
Meet URLの生成、ホストとしての参加、Auto-Admit機能の制御を行う
"""

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import psutil
from google.apps import meet_v2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from ..config import Config
from .webdriver_manager import (
    cleanup_webdriver,
    get_webdriver,
    get_webdriver_chrome_pid,
    is_webdriver_active,
    release_webdriver,
)

logger = logging.getLogger(__name__)


class MeetManager:
    """Google Meet管理クラス（共有WebDriverを使用）"""

    # Google Meet API スコープ
    SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]

    # 待機時間設定
    BUTTON_WAIT_TIMEOUT = 10

    def __init__(self):
        self.driver: webdriver.Chrome | None = None
        self.meet_url: str | None = None
        self.creds: Any = None
        self._process_monitor_thread: threading.Thread | None = None
        self._monitoring = False
        self._on_chrome_exit_callback: Callable[[], None] | None = None

    def create_meet_space(self) -> str:
        """Google Meet APIを使用して新しいMeetスペースを作成"""
        self._authenticate()

        try:
            client = meet_v2.SpacesServiceClient(credentials=self.creds)
            request = meet_v2.CreateSpaceRequest()
            response = client.create_space(request=request)
            meet_url = response.meeting_uri
            return meet_url
        except Exception:
            logger.error("Meetスペースの作成に失敗しました")
            raise

    def _authenticate(self) -> None:
        """Google APIの認証処理"""
        token_path = Path(__file__).parent.parent.parent / "token.json"
        credentials_path = Path(__file__).parent.parent.parent / "credentials.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        "認証情報ファイル (credentials.json) が見つかりません。"
                        "Google Cloud Consoleからダウンロードしてください。"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token:
                token.write(creds.to_json())

        self.creds = creds

    def setup_browser(self) -> None:
        """共有WebDriverインスタンスを取得してセットアップ"""

        try:
            # 共有WebDriverインスタンスを取得
            self.driver = get_webdriver(headless=False)
            logger.info("共有WebDriverインスタンスを取得しました")
        except Exception as e:
            logger.error(f"共有WebDriverの取得に失敗: {e}")
            raise

    def join_as_host(self, meet_url: str) -> None:
        """Meetにホストとして参加"""
        if not self.driver:
            raise ValueError("ブラウザが初期化されていません")

        self.driver.get(meet_url)

        # 参加ボタンをクリック
        join_button = None
        try:
            join_button = WebDriverWait(self.driver, self.BUTTON_WAIT_TIMEOUT).until(
                expected_conditions.element_to_be_clickable(
                    (By.XPATH, Config.GoogleMeet.JOIN_BUTTON_XPATH)
                )
            )
        except TimeoutException:
            join_button = None

        if join_button:
            join_button.click()
        else:
            raise TimeoutException("参加ボタンが見つかりませんでした")

    def enable_auto_admit(self) -> None:
        """Auto-Admit機能を有効化"""
        if not self.driver:
            raise ValueError("ブラウザが初期化されていません")

        logger.info("Auto-Admit機能を有効化中...")

        auto_admit_button = None
        try:
            auto_admit_button = WebDriverWait(
                self.driver, self.BUTTON_WAIT_TIMEOUT
            ).until(
                expected_conditions.element_to_be_clickable(
                    (By.XPATH, Config.GoogleMeet.AUTO_ADMIT_BUTTON_XPATH)
                )
            )
        except TimeoutException:
            auto_admit_button = None

        if auto_admit_button:
            is_pressed = auto_admit_button.get_attribute("aria-pressed") == "true"
            if not is_pressed:
                auto_admit_button.click()
                logger.info("Auto-Admit機能を有効にしました")
            else:
                logger.info("Auto-Admit機能は既に有効です")
        else:
            logger.warning("Auto-Admitボタンが見つかりませんでした")

    def is_session_active(self) -> bool:
        """Chromeとセッションが有効かどうかを確認"""
        try:
            if not self.driver:
                return False

            # ChromeDriverが終了していないかチェック
            _ = self.driver.current_url

            # ページタイトルやURLでMeetから退出していないかチェック
            current_url = self.driver.current_url
            if "meet.google.com" not in current_url:
                return False

            # ページが会議画面から外れていないかチェック（ホーム画面に戻る ってソースにあるか）
            return Config.GoogleMeet.HOME_BUTTON_TEXT not in self.driver.page_source

        except Exception:
            # ChromeDriverが終了している場合やその他のエラー
            return False

    def set_chrome_exit_callback(self, callback: Callable[[], None]) -> None:
        """Chrome終了時のコールバックを設定"""
        self._on_chrome_exit_callback = callback

    def start_process_monitoring(self) -> None:
        """Chromeプロセスの監視を開始"""

        if not self._monitoring:
            self._monitoring = True
            self._process_monitor_thread = threading.Thread(
                target=self._monitor_chrome_process, daemon=True
            )
            self._process_monitor_thread.start()
            logger.info("Chromeプロセス監視を開始しました")

    def stop_process_monitoring(self) -> None:
        """Chromeプロセスの監視を停止"""
        self._monitoring = False
        if self._process_monitor_thread and self._process_monitor_thread.is_alive():
            self._process_monitor_thread.join(timeout=2)
        logger.info("Chromeプロセス監視を停止しました")

    def _monitor_chrome_process(self) -> None:
        """Chromeプロセスを監視"""

        while self._monitoring:
            try:
                # 共有WebDriverの状態チェック
                if not is_webdriver_active():
                    logger.info("共有WebDriverが終了しました")
                    if self._on_chrome_exit_callback:
                        self._on_chrome_exit_callback()
                    break

                # PIDによるプロセス監視
                chrome_pid = get_webdriver_chrome_pid()
                if chrome_pid:
                    try:
                        chrome_process = psutil.Process(chrome_pid)
                        if not chrome_process.is_running():
                            logger.info(
                                f"Chromeプロセス (PID: {chrome_pid}) が終了しました"
                            )
                            if self._on_chrome_exit_callback:
                                self._on_chrome_exit_callback()
                            break
                    except psutil.NoSuchProcess:
                        logger.info(
                            f"Chromeプロセス (PID: {chrome_pid}) が見つかりません"
                        )
                        if self._on_chrome_exit_callback:
                            self._on_chrome_exit_callback()
                        break

                # Meetセッション状態チェック
                if not self.is_session_active():
                    logger.info("Meetセッションが終了しました")
                    if self._on_chrome_exit_callback:
                        self._on_chrome_exit_callback()
                    break

                time.sleep(2)  # 2秒ごとにチェック

            except Exception as e:
                logger.error(f"プロセス監視エラー: {e}")
                time.sleep(5)

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""

        self.stop_process_monitoring()
        if self.driver:
            try:
                # 共有WebDriverの参照を解放
                release_webdriver()
                self.driver = None
                logger.info("MeetManagerのクリーンアップが完了しました")
            except Exception as e:
                logger.error(f"クリーンアップエラー: {e}")

    @classmethod
    def cleanup_shared_driver(cls) -> None:
        """共有ドライバーのクリーンアップ（互換性のため残す）"""
        cleanup_webdriver()
