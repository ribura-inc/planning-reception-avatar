"""
Google Meet管理クラス（リモートPC用）
Meet URLの生成、ホストとしての参加、Auto-Admit機能の制御を行う
"""

import time
from pathlib import Path
from typing import Any

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


class MeetManager:
    """Google Meet管理クラス"""

    # Google Meet API スコープ
    SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]

    # 待機時間設定
    PAGE_LOAD_WAIT = 5
    BUTTON_WAIT_TIMEOUT = 10

    # 拡張機能情報
    AUTO_ADMIT_EXTENSION_URL = "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb"
    SCREEN_CAPTURE_EXTENSION_URL = "https://chromewebstore.google.com/detail/screen-capture-virtual-ca/jcnomcmilppjoogdhhnadpcabpdlikmc"

    # XPath定義
    XPATH_JOIN_BUTTON = [
        "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/..",
        "//span[contains(text(), '参加') or contains(text(), 'Join')]/..",
        "//button[contains(@aria-label, '参加') or contains(@aria-label, 'Join')]",
    ]
    XPATH_AUTO_ADMIT_BUTTON = ["//button[@aria-label='Toggle Auto-Admit']"]

    # Chrome Web Store XPath定義
    XPATH_EXTENSION_REMOVE_BUTTON = [
        "//span[contains(text(), 'Chrome から削除') or contains(text(), 'Remove from Chrome')]/..",
    ]
    XPATH_EXTENSION_ADD_BUTTON = [
        "//span[contains(text(), 'Chrome に追加') or contains(text(), 'Add to Chrome')]/..",
    ]

    def __init__(self):
        self.driver: webdriver.Chrome | None = None
        self.meet_url: str | None = None
        self.creds: Any = None
        self.profile_dir = (
            Path(__file__).parent.parent.parent / ".chrome-profile-remote"
        )

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

    def join_as_host(self, meet_url: str) -> None:
        """Meetにホストとして参加"""
        if not self.driver:
            raise ValueError("ブラウザが初期化されていません")

        print(f"Meeting URLを開く: {meet_url}")
        self.driver.get(meet_url)
        time.sleep(self.PAGE_LOAD_WAIT)

        # 参加ボタンをクリック
        join_button = None
        for xpath in self.XPATH_JOIN_BUTTON:
            try:
                join_button = WebDriverWait(
                    self.driver, self.BUTTON_WAIT_TIMEOUT
                ).until(expected_conditions.element_to_be_clickable((By.XPATH, xpath)))
                break
            except TimeoutException:
                continue

        if join_button:
            join_button.click()
            print("会議に参加しました")
            time.sleep(3)
        else:
            raise TimeoutException("参加ボタンが見つかりませんでした")

    def enable_auto_admit(self) -> None:
        """Auto-Admit機能を有効化"""
        if not self.driver:
            raise ValueError("ブラウザが初期化されていません")

        print("Auto-Admit機能を有効化中...")
        time.sleep(5)

        auto_admit_button = None
        for xpath in self.XPATH_AUTO_ADMIT_BUTTON:
            try:
                auto_admit_button = WebDriverWait(
                    self.driver, self.BUTTON_WAIT_TIMEOUT
                ).until(expected_conditions.element_to_be_clickable((By.XPATH, xpath)))
                break
            except TimeoutException:
                continue

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
        for xpath in self.XPATH_EXTENSION_REMOVE_BUTTON:
            try:
                WebDriverWait(self.driver, 3).until(
                    expected_conditions.presence_of_element_located((By.XPATH, xpath))
                )
                print(f"{extension_name}拡張機能は既にインストールされています")
                return True
            except TimeoutException:
                continue

        # 「Chrome に追加」ボタンが存在するかチェック（未インストールの場合）
        for xpath in self.XPATH_EXTENSION_ADD_BUTTON:
            try:
                WebDriverWait(self.driver, 3).until(
                    expected_conditions.presence_of_element_located((By.XPATH, xpath))
                )
                print(f"{extension_name}拡張機能がインストールされていません")
                return False
            except TimeoutException:
                continue

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

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        if self.driver:
            self.driver.quit()
            self.driver = None
