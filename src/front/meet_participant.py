"""
Meet参加クラス（フロントPC用）
受信したMeet URLに自動参加する
"""

import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

# ロギング設定
logger = logging.getLogger(__name__)


class MeetParticipant:
    """Google Meet参加管理クラス"""

    # 待機時間設定
    PAGE_LOAD_WAIT = 3
    BUTTON_WAIT_TIMEOUT = 10
    POPUP_WAIT = 10

    # XPath定義
    XPATH_JOIN_BUTTON = (
        "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/..|"
        "//span[contains(text(), '参加') or contains(text(), 'Join')]/..|"
        "//button[contains(@aria-label, '参加') or contains(@aria-label, 'Join')]"
    )
    XPATH_NAME_INPUT = "//input[@placeholder='名前' or @placeholder='Your name']"
    XPATH_REQUEST_JOIN = "//span[contains(text(), '参加をリクエスト') or contains(text(), 'Ask to join')]/.."
    XPATH_GEMINI_JOIN = (
        "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
    )
    XPATH_LEAVE_BUTTON = (
        "//button[@aria-label='通話から退出' or @aria-label='Leave call']"
    )

    def __init__(self, use_profile: bool = True, display_name: str = "Reception"):
        """
        Args:
            use_profile: Chromeプロファイルを使用するか
            display_name: 表示名
        """
        self.use_profile = use_profile
        self.display_name = display_name
        self.driver: webdriver.Chrome | None = None
        self.profile_dir = Path(__file__).parent.parent.parent / ".chrome-profile-front"

    def setup_browser(self) -> None:
        """Chromeブラウザのセットアップ"""
        options = Options()

        if self.use_profile:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--profile-directory=Default")

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

            if self.use_profile:
                return self._join_as_logged_in_user()
            else:
                return self._join_as_guest()

        except Exception as e:
            logger.error(f"Meet参加エラー: {e}")
            return False

    def _join_as_logged_in_user(self) -> bool:
        """ログイン済みユーザーとして参加"""
        try:
            logger.info("ログイン済みユーザーとして参加")

            if not self.driver:
                return False
            join_button = WebDriverWait(self.driver, self.BUTTON_WAIT_TIMEOUT).until(
                expected_conditions.element_to_be_clickable((By.XPATH, self.XPATH_JOIN_BUTTON))
            )
            join_button.click()
            logger.info("会議に参加しました")

            # Geminiポップアップ処理
            self._handle_gemini_popup()
            return True

        except TimeoutException:
            logger.error("参加ボタンが見つかりませんでした")
            return False

    def _join_as_guest(self) -> bool:
        """ゲストとして参加"""
        try:
            logger.info(f"ゲストとして参加: {self.display_name}")

            # 名前入力
            if not self.driver:
                return False
            name_input = WebDriverWait(self.driver, self.BUTTON_WAIT_TIMEOUT).until(
                expected_conditions.presence_of_element_located((By.XPATH, self.XPATH_NAME_INPUT))
            )
            name_input.clear()
            name_input.send_keys(self.display_name)
            logger.info(f"表示名を入力: {self.display_name}")

            # 参加リクエスト
            join_button = self.driver.find_element(By.XPATH, self.XPATH_REQUEST_JOIN)
            join_button.click()
            logger.info("参加をリクエストしました")

            # Geminiポップアップ処理
            self._handle_gemini_popup()
            return True

        except Exception as e:
            logger.error(f"ゲスト参加エラー: {e}")
            return False

    def _handle_gemini_popup(self) -> None:
        """Geminiメモ作成ポップアップの処理"""
        try:
            time.sleep(self.POPUP_WAIT)
            gemini_join_button = self.driver.find_element(
                By.XPATH, self.XPATH_GEMINI_JOIN
            )
            gemini_join_button.click()
            logger.info("Geminiメモ作成確認を処理しました")
        except Exception:
            # ポップアップが出ない場合は何もしない
            pass

    def leave_meeting(self) -> bool:
        """会議から退出"""
        try:
            if not self.driver:
                return True

            leave_button = WebDriverWait(self.driver, 5).until(
                expected_conditions.element_to_be_clickable((By.XPATH, self.XPATH_LEAVE_BUTTON))
            )
            leave_button.click()
            logger.info("会議から退出しました")
            time.sleep(2)
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
            self.driver.find_element(By.XPATH, self.XPATH_LEAVE_BUTTON)
            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("ブラウザを終了しました")
        except Exception as e:
            logger.error(f"ブラウザ終了エラー: {e}")

    def __enter__(self) -> "MeetParticipant":
        """コンテキストマネージャーのエントリ"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """コンテキストマネージャーの終了処理"""
        self.cleanup()
