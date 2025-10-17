"""Google Meet管理クラス（リモートPC用).

Meet URLの生成、ホストとしての参加、Auto-Admit機能の制御を行う
"""

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import psutil
from google.apps import meet_v2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.utils.selenium_utils import retry_operation, wait_for_element_safely
from src.utils.slack import SessionLocation, notify_error

from .webdriver_manager import (
    get_webdriver,
    get_webdriver_chrome_pid,
    is_webdriver_active,
    release_webdriver,
)

logger = logging.getLogger(__name__)


class MeetManager:
    """Google Meet管理クラス（共有WebDriverを使用）"""

    # Google Meet API スコープ
    SCOPES: ClassVar[list[str]] = ["https://www.googleapis.com/auth/meetings.space.created"]

    # 待機時間設定
    BUTTON_WAIT_TIMEOUT = 10

    AUTO_ADMIT_EXTENSION_URL: ClassVar[str] = (
        "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb"
    )

    def __init__(self) -> None:
        self.driver: webdriver.Chrome | None = None
        self.meet_url: str | None = None
        self.creds: Any = None
        self._process_monitor_thread: threading.Thread | None = None
        self._monitoring = False
        self._on_chrome_exit_callback: Callable[[], None] | None = None

    def _run_with_temp_driver(
        self,
        context_log: str,
        action: Callable[[webdriver.Chrome], tuple[bool, str]],
        error_log: str,
        error_message: str,
        cleanup_log: str,
    ) -> tuple[bool, str]:
        temp_driver: webdriver.Chrome | None = None
        try:
            logger.info(context_log)
            temp_driver = get_webdriver(headless=True)
            return action(temp_driver)
        except Exception:
            logger.exception(error_log)
            return False, error_message
        finally:
            if temp_driver:
                try:
                    release_webdriver()
                    logger.info(cleanup_log)
                except Exception:
                    logger.exception("一時driver解放エラー")

    def create_meet_space(self) -> str:
        """Google Meet APIを使用して新しいMeetスペースを作成"""
        self._authenticate()

        try:
            client = meet_v2.SpacesServiceClient(credentials=self.creds)
            request = meet_v2.CreateSpaceRequest()
            response = client.create_space(request=request)
            return response.meeting_uri  # noqa: TRY300
        except Exception as e:
            logger.exception("Meetスペースの作成に失敗しました")
            notify_error(
                error=e,
                context="Meetスペース作成失敗",
                additional_info={},
                location=SessionLocation.REMOTE,
            )
            raise

    def _authenticate(self) -> None:
        """Google APIの認証処理"""
        token_path = Config.CONFIG_DIR / "token.json"
        credentials_path = Path(__file__).parent.parent.parent / "credentials.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    msg = (
                        "認証情報ファイル (credentials.json) が見つかりません。"
                        "Google Cloud Consoleからダウンロードしてください。"
                    )
                    raise FileNotFoundError(
                        msg,
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path),
                    self.SCOPES,
                )
                creds = flow.run_local_server(port=0)

            with token_path.open("w") as token:
                token.write(creds.to_json())

        self.creds = creds

    def setup_browser(self) -> None:
        """共有WebDriverインスタンスを取得してセットアップ"""
        try:
            # 共有WebDriverインスタンスを取得
            self.driver = get_webdriver(headless=False)
            logger.info("共有WebDriverインスタンスを取得しました")
        except Exception as e:
            logger.exception("共有WebDriverの取得に失敗")
            notify_error(
                error=e,
                context="WebDriver取得失敗",
                additional_info={},
                location=SessionLocation.REMOTE,
            )
            raise

    def join_as_host(self, meet_url: str) -> None:
        """Meetにホストとして参加"""
        if not self.driver:
            msg = "ブラウザが初期化されていません"
            raise ValueError(msg)

        self.driver.get(meet_url)

        def _attempt_join() -> bool:
            """参加試行の実装"""
            # 参加ボタンを安全に待機
            join_button = wait_for_element_safely(
                self.driver,
                By.XPATH,
                Config.GoogleMeet.JOIN_BUTTON_XPATH,
            )

            if join_button:
                join_button.click()
                logger.info("ホストとして参加ボタンをクリックしました")
                return True

            logger.error("参加ボタンが見つかりませんでした")
            return False

        # リトライ機能付きで実行
        if not retry_operation(_attempt_join, "ホスト参加", location=SessionLocation.REMOTE):
            msg = "参加ボタンが見つかりませんでした"
            raise TimeoutException(msg)

    def enable_auto_admit(self) -> None:
        """Auto-Admit機能を有効化"""
        if not self.driver:
            msg = "ブラウザが初期化されていません"
            raise ValueError(msg)

        logger.info("Auto-Admit機能を有効化中...")

        def _attempt_enable_auto_admit() -> bool:
            """Auto-Admit有効化試行の実装"""
            # Auto-Admitボタンを安全に待機
            auto_admit_button = wait_for_element_safely(
                self.driver,
                By.XPATH,
                Config.GoogleMeet.AUTO_ADMIT_BUTTON_XPATH,
            )

            if auto_admit_button:
                is_pressed = auto_admit_button.get_attribute("aria-pressed") == "true"
                if not is_pressed:
                    auto_admit_button.click()
                    logger.info("Auto-Admit機能を有効にしました")
                else:
                    logger.info("Auto-Admit機能は既に有効です")
                return True

            logger.warning("Auto-Admitボタンが見つかりませんでした")
            return False

        # リトライ機能付きで実行（失敗してもwarningで続行）
        retry_operation(_attempt_enable_auto_admit, "Auto-Admit有効化", location=SessionLocation.REMOTE)

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
        except Exception:  # noqa: BLE001
            # ChromeDriverが終了している場合やその他のエラー
            return False
        else:
            return Config.GoogleMeet.HOME_BUTTON_TEXT not in self.driver.page_source

    def set_chrome_exit_callback(self, callback: Callable[[], None]) -> None:
        """Chrome終了時のコールバックを設定"""
        self._on_chrome_exit_callback = callback

    def start_process_monitoring(self) -> None:
        """Chromeプロセスの監視を開始"""
        if not self._monitoring:
            self._monitoring = True
            self._process_monitor_thread = threading.Thread(
                target=self._monitor_chrome_process,
                daemon=True,
            )
            self._process_monitor_thread.start()
            logger.info("Chromeプロセス監視を開始しました")

    def stop_process_monitoring(self) -> None:
        """Chromeプロセスの監視を停止"""
        self._monitoring = False
        if self._process_monitor_thread and self._process_monitor_thread.is_alive():
            self._process_monitor_thread.join(timeout=2)
        logger.info("Chromeプロセス監視を停止しました")

    def _monitor_chrome_process(self) -> None:  # noqa: C901
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
                                f"Chromeプロセス (PID: {chrome_pid}) が終了しました",
                            )
                            if self._on_chrome_exit_callback:
                                self._on_chrome_exit_callback()
                            break
                    except psutil.NoSuchProcess:
                        logger.info(
                            f"Chromeプロセス (PID: {chrome_pid}) が見つかりません",
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

                time.sleep(Config.GoogleMeet.PROCESS_MONITOR_INTERVAL)  # プロセス監視間隔

            except Exception:
                logger.exception("プロセス監視エラー")
                time.sleep(Config.GoogleMeet.PROCESS_MONITOR_ERROR_WAIT)

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        self.stop_process_monitoring()
        if self.driver:
            try:
                # 共有WebDriverの参照を解放
                release_webdriver()
                self.driver = None
                logger.info("MeetManagerのクリーンアップが完了しました")
            except Exception:
                logger.exception("クリーンアップエラー")

    def check_google_login(self) -> tuple[bool, str]:
        """Googleアカウントのログイン状態を確認（headless実行、終了後自動クリーンアップ）.

        Returns:
            (成功フラグ, メッセージ)
        """

        def _action(driver: webdriver.Chrome) -> tuple[bool, str]:
            driver.get("https://myaccount.google.com")
            time.sleep(3)

            current_url = driver.current_url
            if "myaccount.google.com" in current_url and "signin" not in current_url:
                logger.info("✅ Googleアカウントにログイン済み")
                return True, "Googleアカウントにログイン済みです"

            logger.warning("❌ Googleアカウントにログインしていません")
            return False, "Googleアカウントにログインしていません"

        return self._run_with_temp_driver(
            "Googleアカウントのログイン状態を確認中...",
            _action,
            "Googleログイン確認中にエラー",
            "Googleログイン確認中にエラーが発生しました",
            "一時driver（Googleログイン確認用）をクリーンアップしました",
        )

    def check_extension_installed(self) -> tuple[bool, str]:
        """Auto-Admit拡張機能のインストール状態を確認（headless実行、終了後自動クリーンアップ）.

        Returns:
            (成功フラグ, メッセージ)
        """

        def _action(driver: webdriver.Chrome) -> tuple[bool, str]:
            driver.get(self.AUTO_ADMIT_EXTENSION_URL)
            time.sleep(4)

            try:
                WebDriverWait(driver, 3).until(
                    lambda d: d.find_element(By.XPATH, Config.ChromeExtension.REMOVE_BUTTON_XPATH),
                )
            except TimeoutException:
                pass
            else:
                logger.info("✅ Auto-Admit拡張機能がインストール済み")
                return True, "Auto-Admit拡張機能はインストール済みです"

            try:
                WebDriverWait(driver, 3).until(
                    lambda d: d.find_element(By.XPATH, Config.ChromeExtension.ADD_BUTTON_XPATH),
                )
            except TimeoutException:
                pass
            else:
                logger.warning("❌ Auto-Admit拡張機能がインストールされていません")
                return False, f"Auto-Admit拡張機能をインストールしてください: {self.AUTO_ADMIT_EXTENSION_URL}"

            return False, "拡張機能のインストール状態を確認できませんでした"

        return self._run_with_temp_driver(
            "Auto-Admit拡張機能の確認中...",
            _action,
            "拡張機能確認中にエラー",
            "拡張機能確認中にエラーが発生しました",
            "一時driver（拡張機能確認用）をクリーンアップしました",
        )

    def open_google_login_page(self) -> None:
        """Googleログインページを開く"""
        try:
            if not self.driver:
                self.setup_browser()
            self.driver.get("https://accounts.google.com/")
            logger.info("Googleログインページを開きました")
        except Exception:
            logger.exception("Googleログインページを開けませんでした")

    def open_extension_page(self) -> None:
        """Auto-Admit拡張機能のページを開く"""
        try:
            if not self.driver:
                self.setup_browser()
            self.driver.get(self.AUTO_ADMIT_EXTENSION_URL)
            logger.info("拡張機能ページを開きました")
        except Exception:
            logger.exception("拡張機能ページを開けませんでした")
