"""
Meet参加クラス（フロントPC用）
受信したMeet URLに自動参加する
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import psutil
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from ..config import Config

# ロギング設定
logger = logging.getLogger(__name__)


class MeetParticipant:
    """Google Meet参加管理クラス"""

    # 待機時間設定（最適化済み）
    PAGE_LOAD_WAIT = 1.5
    BUTTON_WAIT_TIMEOUT = 15
    POPUP_WAIT = 90

    def __init__(self, display_name: str = "Reception"):
        """
        Args:
            display_name: 表示名
        """
        self.display_name = display_name
        self.driver: webdriver.Chrome | None = None
        self._process_monitor_thread: threading.Thread | None = None
        self._monitoring = False
        self._on_chrome_exit_callback: Callable[[], None] | None = None
        self._chrome_pid: int | None = None

    def setup_browser(self) -> None:
        """Chromeブラウザのセットアップ"""
        options = Options()

        # 言語設定
        options.add_argument("--lang=ja")

        # メディアストリーム設定
        options.add_experimental_option(
            "prefs",
            {
                "intl.accept_languages": "ja,en-US,en",
                "profile.default_content_setting_values.media_stream_mic": 1,
                "profile.default_content_setting_values.media_stream_camera": 1,
                "profile.default_content_setting_values.geolocation": 0,
                "profile.default_content_setting_values.notifications": 2,
            },
        )

        # その他オプション
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)

        # ChromeのPIDを取得
        try:
            # ChromeDriverのPIDから実際のChromeプロセスを特定
            if hasattr(self.driver.service, "process"):
                driver_pid = self.driver.service.process.pid
                # ChromeDriverの子プロセスとしてChromeを探す
                parent_process = psutil.Process(driver_pid)
                for child in parent_process.children(recursive=True):
                    if "chrome" in child.name().lower():
                        self._chrome_pid = child.pid
                        break
        except Exception as e:
            logger.error(f"Chrome PID取得エラー: {e}")

    def validate_meet_url(self, url: str) -> bool:
        """Meet URLの妥当性を検証"""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ["meet.google.com"]
        except Exception:
            return False

    def join_meeting(self, meet_url: str) -> bool:
        """Meetに参加"""
        try:
            if not self.validate_meet_url(meet_url):
                logger.error(f"無効なMeet URL: {meet_url}")
                return False

            logger.info(f"Meet URLを開く: {meet_url}")

            # ブラウザセットアップ（まだセットアップされていない場合）
            if not self.driver:
                self.setup_browser()

            self.driver.get(meet_url)
            time.sleep(self.PAGE_LOAD_WAIT)

            # フロントPCは常にゲストとして参加
            return self._join_as_guest()

        except Exception as e:
            logger.error(f"Meet参加エラー: {e}")
            return False

    def _join_as_guest(self) -> bool:
        """ゲストとして参加"""
        try:
            logger.info(f"ゲストとして参加: {self.display_name}")

            # 名前入力
            if not self.driver:
                return False
            name_input = WebDriverWait(self.driver, self.BUTTON_WAIT_TIMEOUT).until(
                expected_conditions.presence_of_element_located(
                    (By.XPATH, Config.GoogleMeet.NAME_INPUT_XPATH)
                )
            )
            name_input.clear()
            name_input.send_keys(self.display_name)
            logger.info(f"表示名を入力: {self.display_name}")

            # 参加リクエスト
            join_button = self.driver.find_element(
                By.XPATH, Config.GoogleMeet.REQUEST_JOIN_BUTTON_XPATH
            )
            join_button.click()
            logger.info("参加をリクエストしました")

            # Geminiポップアップ処理
            self._handle_gemini_popup()
            return True

        except Exception as e:
            logger.error(f"ゲスト参加エラー: {e}")
            return False

    def _handle_gemini_popup(self) -> None:
        """Geminiメモ作成ポップアップの処理（改良版）"""
        max_wait_time = self.POPUP_WAIT
        check_interval = 0.5
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                # Gemini参加ボタンをチェック
                gemini_join_button = self.driver.find_element(
                    By.XPATH, Config.GoogleMeet.GEMINI_JOIN_BUTTON_XPATH
                )
                gemini_join_button.click()
                logger.info("Geminiメモ作成確認を処理しました")
                return
            except Exception:
                pass

            time.sleep(check_interval)
            elapsed_time += check_interval

    def leave_meeting(self) -> bool:
        """会議から退出"""
        try:
            if not self.driver:
                return True

            leave_button = WebDriverWait(self.driver, 5).until(
                expected_conditions.element_to_be_clickable(
                    (By.XPATH, Config.GoogleMeet.LEAVE_BUTTON_XPATH)
                )
            )
            leave_button.click()
            logger.info("会議から退出しました")
            time.sleep(1)
            return True

        except TimeoutException:
            logger.warning("退出ボタンが見つかりませんでした")
            return False
        except Exception as e:
            logger.error(f"退出エラー: {e}")
            return False

    def is_in_meeting(self) -> bool:
        """会議中かどうかを確認"""
        if not self.driver:
            return False

        try:
            # 退出ボタンの存在で会議中かを判定
            self.driver.find_element(By.XPATH, Config.GoogleMeet.LEAVE_BUTTON_XPATH)
            return True
        except Exception:
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
                # ドライバーの状態チェック
                if not self.driver:
                    logger.info("Chromeドライバーが終了しました")
                    if self._on_chrome_exit_callback:
                        self._on_chrome_exit_callback()
                    break

                # PIDによるプロセス監視
                if self._chrome_pid:
                    try:
                        chrome_process = psutil.Process(self._chrome_pid)
                        if not chrome_process.is_running():
                            logger.info(
                                f"Chromeプロセス (PID: {self._chrome_pid}) が終了しました"
                            )
                            if self._on_chrome_exit_callback:
                                self._on_chrome_exit_callback()
                            break
                    except psutil.NoSuchProcess:
                        logger.info(
                            f"Chromeプロセス (PID: {self._chrome_pid}) が見つかりません"
                        )
                        if self._on_chrome_exit_callback:
                            self._on_chrome_exit_callback()
                        break

                # Meetセッション状態チェック
                if not self.is_in_meeting():
                    try:
                        # Meetから退出したかチェック
                        current_url = self.driver.current_url
                        if (
                            "meet.google.com" not in current_url
                            or Config.GoogleMeet.HOME_BUTTON_TEXT
                            in self.driver.page_source
                        ):
                            logger.info("Meetから退出しました")
                            if self._on_chrome_exit_callback:
                                self._on_chrome_exit_callback()
                            break
                    except Exception:
                        pass

                time.sleep(2)  # 2秒ごとにチェック

            except Exception as e:
                logger.error(f"プロセス監視エラー: {e}")
                time.sleep(5)

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        self.stop_process_monitoring()
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self._chrome_pid = None
                logger.info("ブラウザを終了しました")
        except Exception as e:
            logger.error(f"ブラウザ終了エラー: {e}")

    def __enter__(self) -> "MeetParticipant":
        """コンテキストマネージャーのエントリ"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """コンテキストマネージャーの終了処理"""
        self.cleanup()
