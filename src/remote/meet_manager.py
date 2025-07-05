"""
Google Meet管理クラス（リモートPC用）
Meet URLの生成、ホストとしての参加、Auto-Admit機能の制御を行う
"""

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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from ..config import Config


class MeetManager:
    """Google Meet管理クラス"""

    # Google Meet API スコープ
    SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]

    # 待機時間設定
    BUTTON_WAIT_TIMEOUT = 10

    # 拡張機能情報
    AUTO_ADMIT_EXTENSION_URL = "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb"
    SCREEN_CAPTURE_EXTENSION_URL = "https://chromewebstore.google.com/detail/screen-capture-virtual-ca/jcnomcmilppjoogdhhnadpcabpdlikmc"

    def __init__(self):
        self.driver: webdriver.Chrome | None = None
        self.meet_url: str | None = None
        self.creds: Any = None
        self.profile_dir = (
            Path(__file__).parent.parent.parent / ".chrome-profile-remote"
        )
        self._process_monitor_thread: threading.Thread | None = None
        self._monitoring = False
        self._on_chrome_exit_callback: Callable[[], None] | None = None
        self._chrome_pid: int | None = None

    def create_meet_space(self) -> str:
        """Google Meet APIを使用して新しいMeetスペースを作成"""
        self._authenticate()

        try:
            client = meet_v2.SpacesServiceClient(credentials=self.creds)
            request = meet_v2.CreateSpaceRequest()
            response = client.create_space(request=request)
            meet_url = response.meeting_uri
            print(f"新しいMeetスペースを作成: {meet_url}")
            return meet_url
        except Exception as error:
            print(f"Meet APIエラー: {error}")
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
        """Chromeブラウザのセットアップ"""
        options = Options()

        # プロファイルディレクトリ設定
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--profile-directory=Default")

        # 言語とメディア設定
        options.add_argument("--lang=ja")
        options.add_experimental_option(
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
        options.add_argument("--enable-usermedia-screen-capturing")
        # options.add_argument("--use-fake-ui-for-media-stream") # これは有効にしたらダメ
        options.add_argument("--auto-select-desktop-capture-source=VTube Studio")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # ウィンドウサイズ設定
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
            print(f"Chrome PID取得エラー: {e}")

    def join_as_host(self, meet_url: str) -> None:
        """Meetにホストとして参加"""
        if not self.driver:
            raise ValueError("ブラウザが初期化されていません")

        print(f"Meeting URLを開く: {meet_url}")
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
            print("会議に参加しました")
        else:
            raise TimeoutException("参加ボタンが見つかりませんでした")

    def enable_auto_admit(self) -> None:
        """Auto-Admit機能を有効化"""
        if not self.driver:
            raise ValueError("ブラウザが初期化されていません")

        print("Auto-Admit機能を有効化中...")

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
                print("Auto-Admit機能を有効にしました")
            else:
                print("Auto-Admit機能は既に有効です")
        else:
            print("Auto-Admitボタンが見つかりませんでした")

    def check_extension(self, extension_url: str, extension_name: str) -> bool:
        """拡張機能がインストールされているか確認"""
        if not self.driver:
            return False

        print(f"{extension_name}拡張機能の確認中...")

        # 拡張機能ページを開く
        self.driver.get(extension_url)
        time.sleep(3)

        # 「Chrome から削除」ボタンが存在するかチェック（インストール済みの場合）
        try:
            WebDriverWait(self.driver, 3).until(
                expected_conditions.presence_of_element_located(
                    (By.XPATH, Config.ChromeExtension.REMOVE_BUTTON_XPATH)
                )
            )
            print(f"{extension_name}拡張機能は既にインストールされています")
            return True
        except TimeoutException:
            pass

        # 「Chrome に追加」ボタンが存在するかチェック（未インストールの場合）
        try:
            WebDriverWait(self.driver, 3).until(
                expected_conditions.presence_of_element_located(
                    (By.XPATH, Config.ChromeExtension.ADD_BUTTON_XPATH)
                )
            )
            print(f"{extension_name}拡張機能がインストールされていません")
            return False
        except TimeoutException:
            pass

        print(f"{extension_name}拡張機能の状態を確認できませんでした")
        return False

    def ensure_google_login(self) -> bool:
        """Googleアカウントへのログイン確認"""
        if not self.driver:
            return False

        print("Googleアカウントのログイン状態を確認中...")
        self.driver.get("https://myaccount.google.com/")
        time.sleep(3)

        try:
            current_url = self.driver.current_url
            if "myaccount.google.com" in current_url and "signin" not in current_url:
                print("Googleアカウントにログイン済みです")
                return True
        except Exception:
            pass

        print("Googleアカウントにログインしてください...")
        self.driver.get("https://accounts.google.com/signin")
        print("ブラウザでMeet APIで使用したGoogleアカウントにログインしてください。")
        input("ログイン完了後、Enterキーを押してください: ")
        return True

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
            print("Chromeプロセス監視を開始しました")

    def stop_process_monitoring(self) -> None:
        """Chromeプロセスの監視を停止"""
        self._monitoring = False
        if self._process_monitor_thread and self._process_monitor_thread.is_alive():
            self._process_monitor_thread.join(timeout=2)
        print("Chromeプロセス監視を停止しました")

    def _monitor_chrome_process(self) -> None:
        """Chromeプロセスを監視"""
        while self._monitoring:
            try:
                # ドライバーの状態チェック
                if not self.driver:
                    print("Chromeドライバーが終了しました")
                    if self._on_chrome_exit_callback:
                        self._on_chrome_exit_callback()
                    break

                # PIDによるプロセス監視
                if self._chrome_pid:
                    try:
                        chrome_process = psutil.Process(self._chrome_pid)
                        if not chrome_process.is_running():
                            print(
                                f"Chromeプロセス (PID: {self._chrome_pid}) が終了しました"
                            )
                            if self._on_chrome_exit_callback:
                                self._on_chrome_exit_callback()
                            break
                    except psutil.NoSuchProcess:
                        print(
                            f"Chromeプロセス (PID: {self._chrome_pid}) が見つかりません"
                        )
                        if self._on_chrome_exit_callback:
                            self._on_chrome_exit_callback()
                        break

                # Meetセッション状態チェック
                if not self.is_session_active():
                    print("Meetセッションが終了しました")
                    if self._on_chrome_exit_callback:
                        self._on_chrome_exit_callback()
                    break

                time.sleep(2)  # 2秒ごとにチェック

            except Exception as e:
                print(f"プロセス監視エラー: {e}")
                time.sleep(5)

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        self.stop_process_monitoring()
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Chrome終了エラー: {e}")
            finally:
                self.driver = None
                self._chrome_pid = None
