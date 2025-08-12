"""
remoteディレクトリ全体で共有するWebDriverマネージャー
プロファイルディレクトリの競合を回避するために、
単一のWebDriverインスタンスを管理する
"""

import threading
from logging import getLogger
from pathlib import Path

import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from src.config import Config
from src.utils.platform_utils import PlatformUtils

logger = getLogger(__name__)


class WebDriverManager:
    """remote全体で共有するWebDriverマネージャー（Singleton）"""

    _instance: "WebDriverManager | None" = None
    _lock = threading.Lock()

    _driver: webdriver.Chrome | None = None
    _driver_lock = threading.Lock()
    _reference_count = 0
    _chrome_pid: int | None = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        # 初期化は一度だけ実行
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.profile_dir = (
            Path.home() / Config.CONFIG_DIR_PATH / "chrome-profile-remote"
        )

    def get_driver(self, headless: bool = False) -> webdriver.Chrome:
        """共有WebDriverインスタンスを取得"""
        with self._driver_lock:
            self._reference_count += 1

            if self._driver is not None:
                try:
                    # 既存のドライバーが有効かチェック
                    _ = self._driver.current_url
                    logger.info(
                        f"既存のWebDriverインスタンスを再利用 (参照カウント: {self._reference_count})"
                    )
                    return self._driver
                except Exception:
                    # 無効なドライバーをクリーンアップ
                    logger.info("既存のWebDriverが無効になっていたため、再作成します")
                    self._cleanup_driver()

            # 新しいドライバーを作成
            self._driver = self._create_driver(headless=headless)
            self._get_chrome_pid()
            logger.info(
                f"新しいWebDriverインスタンスを作成 (参照カウント: {self._reference_count})"
            )
            return self._driver

    def release_driver(self) -> None:
        """WebDriverインスタンスの参照を解放"""
        with self._driver_lock:
            if self._reference_count > 0:
                self._reference_count -= 1
                logger.info(
                    f"WebDriver参照を解放 (参照カウント: {self._reference_count})"
                )

                # 参照カウントが0になったらドライバーを終了
                if self._reference_count == 0:
                    logger.info("全ての参照が解放されたため、WebDriverを終了します")
                    self._cleanup_driver()

    def force_cleanup(self) -> None:
        """強制的にWebDriverをクリーンアップ"""
        with self._driver_lock:
            self._reference_count = 0
            self._cleanup_driver()
            logger.info("WebDriverを強制終了しました")

    def _create_driver(self, headless: bool = False) -> webdriver.Chrome:
        """新しいWebDriverインスタンスを作成"""
        chrome_options = Options()

        # プロファイルディレクトリ設定
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
        chrome_options.add_argument("--profile-directory=Default")

        if headless:
            # ヘッドレスモード設定
            chrome_options.add_argument("--headless=new")
        else:
            # ヘッドレスモードではない場合の設定
            # 言語とメディア設定
            chrome_options.add_argument("--lang=ja")
            chrome_options.add_experimental_option(
                "prefs",
                {
                    "intl.accept_languages": "ja,en-US,en",
                    "profile.default_content_setting_values.media_stream_mic": 1,
                    "profile.default_content_setting_values.media_stream_camera": 1,
                    "profile.default_content_setting_values.desktop_capture": 1,
                    "profile.default_content_setting_values.geolocation": 0,
                    "profile.default_content_setting_values.notifications": 2,
                },
            )

            # その他オプション
            chrome_options.add_argument("--enable-usermedia-screen-capturing")
            # chrome_options.add_argument("--use-fake-ui-for-media-stream") # これは有効にしたらダメ
            chrome_options.add_argument(
                "--auto-select-desktop-capture-source=VTube Studio"
            )
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("--disable-gpu")

            # ウィンドウサイズ設定
            chrome_options.add_argument("--window-size=1920,1080")

        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=chrome_options)
            if not headless:
                driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.error(f"WebDriverの作成に失敗: {e}")
            raise

    def _get_chrome_pid(self) -> None:
        """ChromeプロセスのPIDを取得"""
        try:
            if self._driver and hasattr(self._driver.service, "process"):
                driver_pid = self._driver.service.process.pid
                parent_process = psutil.Process(driver_pid)
                chrome_process_name = PlatformUtils.get_chrome_process_name()
                for child in parent_process.children(recursive=True):
                    if chrome_process_name.lower() in child.name().lower():
                        self._chrome_pid = child.pid
                        break
        except Exception as e:
            logger.error(f"Chrome PID取得エラー: {e}")

    def _cleanup_driver(self) -> None:
        """WebDriverをクリーンアップ"""
        if self._driver:
            try:
                self._driver.quit()
            except Exception as e:
                logger.error(f"WebDriver終了エラー: {e}")
            finally:
                self._driver = None
                self._chrome_pid = None

    def is_driver_active(self) -> bool:
        """WebDriverが有効かどうかを確認"""
        if not self._driver:
            return False
        try:
            _ = self._driver.current_url
            return True
        except Exception:
            return False

    def get_chrome_pid(self) -> int | None:
        """Chrome プロセスのPIDを取得"""
        return self._chrome_pid


# モジュールレベルでインスタンスを作成（シングルトン）
_webdriver_manager = WebDriverManager()


def get_webdriver(headless: bool = False) -> webdriver.Chrome:
    """共有WebDriverインスタンスを取得"""
    return _webdriver_manager.get_driver(headless=headless)


def release_webdriver() -> None:
    """共有WebDriverインスタンスの参照を解放"""
    _webdriver_manager.release_driver()


def cleanup_webdriver() -> None:
    """共有WebDriverを強制クリーンアップ"""
    _webdriver_manager.force_cleanup()


def is_webdriver_active() -> bool:
    """共有WebDriverが有効かどうかを確認"""
    return _webdriver_manager.is_driver_active()


def get_webdriver_chrome_pid() -> int | None:
    """共有WebDriverのChrome PIDを取得"""
    return _webdriver_manager.get_chrome_pid()
