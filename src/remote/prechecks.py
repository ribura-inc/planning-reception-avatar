"""事前チェック機能（拡張機能・Googleログイン確認）"""

import logging
import time
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..config import Config

logger = logging.getLogger(__name__)


class PrecheckManager:
    """事前チェック機能を管理するクラス（共有WebDriverを使用）"""

    # 拡張機能のURL
    AUTO_ADMIT_EXTENSION_URL = "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb"
    SCREEN_CAPTURE_EXTENSION_URL = "https://chromewebstore.google.com/detail/screen-capture-virtual-ca/jcnomcmilppjoogdhhnadpcabpdlikmc"

    def __init__(self):
        """初期化"""
        self.driver: webdriver.Chrome | None = None
        self.check_results: dict[str, Any] = {
            "google_login": False,
            "auto_admit": False,
            "screen_capture": False,
            "errors": [],
        }

    def _setup_browser(self, headless: bool = True) -> None:
        """共有WebDriverインスタンスを取得してセットアップ"""
        from .webdriver_manager import get_webdriver

        try:
            # 共有WebDriverインスタンスを取得
            self.driver = get_webdriver(headless=headless)
            logger.info("共有WebDriverインスタンスを取得しました")
        except Exception as e:
            logger.error(f"共有WebDriverの取得に失敗: {e}")
            raise

    def check_google_login(self) -> bool:
        """Googleアカウントのログインを確認"""
        try:
            logger.info("Googleアカウントのログイン状態を確認中...")
            if not self.driver:
                self._setup_browser()
                if not self.driver:
                    logger.error("ドライバの初期化に失敗しました")
                    return False

            self.driver.get("https://myaccount.google.com")
            time.sleep(3)

            # ログイン済みかチェック
            try:
                current_url = self.driver.current_url
                if (
                    "myaccount.google.com" in current_url
                    and "signin" not in current_url
                ):
                    logger.info("✅ Googleアカウントにログイン済み")
                    return True
            except Exception:
                logger.warning("❌ Googleアカウントにログインしていません")
                self.check_results["errors"].append(
                    "Googleアカウントにログインしてください"
                )
                return False
        except Exception as e:
            logger.error(f"Googleログイン確認中にエラー: {e}")
            self.check_results["errors"].append(f"Googleログイン確認エラー: {e}")
            return False
        finally:
            self.cleanup()

        return False

    def check_extension(self, extension_url: str, extension_name: str) -> bool:
        """拡張機能がインストールされているか確認"""
        try:
            logger.info(f"{extension_name}拡張機能の確認中...")
            if not self.driver:
                self._setup_browser()
                if not self.driver:
                    logger.error("ドライバの初期化に失敗しました")
                    return False
            # Chrome拡張機能ページを開く
            self.driver.get(extension_url)
            time.sleep(3)

            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, Config.ChromeExtension.REMOVE_BUTTON_XPATH)
                    )
                )
                logger.info(f"✅ {extension_name}拡張機能がインストール済み")
                return True
            except TimeoutException:
                pass

            # 「Chrome に追加」ボタンが存在するかチェック（未インストールの場合）
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, Config.ChromeExtension.ADD_BUTTON_XPATH)
                    )
                )
                logger.warning(
                    f"❌ {extension_name}拡張機能がインストールされていません"
                )
                self.check_results["errors"].append(
                    f"{extension_name}拡張機能をインストールしてください: {extension_url}"
                )
                return False
            except TimeoutException:
                pass

        except Exception as e:
            logger.error(f"{extension_name}拡張機能確認中にエラー: {e}")
            self.check_results["errors"].append(f"{extension_name}確認エラー: {e}")
            return False
        finally:
            self.cleanup()

        return False

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        from .webdriver_manager import release_webdriver

        if self.driver:
            try:
                # 共有WebDriverの参照を解放
                release_webdriver()
                self.driver = None
                logger.info("PrecheckManagerのクリーンアップが完了しました")
            except Exception as e:
                logger.error(f"PrecheckManagerクリーンアップエラー: {e}")
