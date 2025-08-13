"""
Meet参加クラス（フロントPC用）
受信したMeet URLに自動参加する
"""

import logging
import time
from typing import Any
from urllib.parse import urlparse

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

    def is_chrome_running(self) -> bool:
        """Chromeが実行中かチェック"""
        return self.driver is not None

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
        # 全画面モードで起動
        options.add_argument("--start-fullscreen")

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
            join_button = WebDriverWait(self.driver, self.BUTTON_WAIT_TIMEOUT).until(
                expected_conditions.element_to_be_clickable(
                    (By.XPATH, Config.GoogleMeet.REQUEST_JOIN_BUTTON_XPATH)
                )
            )
            join_button.click()
            logger.info("参加をリクエストしました")

            # Geminiポップアップ処理
            # self._handle_gemini_popup() # Ribura垢でない場合は表示されない
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
            return True

        except TimeoutException:
            logger.warning("退出ボタンが見つかりませんでした")
            return False
        except Exception as e:
            logger.error(f"退出エラー: {e}")
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

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """コンテキストマネージャーの終了処理"""
        self.cleanup()
