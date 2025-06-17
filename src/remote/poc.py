#!/usr/bin/env python3
"""
Google Meet自動ホストスクリプト（リモートPC用）
MeetリンクをAPIで生成し、自動で参加してAuto-Admit拡張機能を有効化する
"""

import sys
import time
from pathlib import Path

from google.apps import meet_v2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 定数定義
PAGE_LOAD_WAIT = 5  # ページ読み込み待機時間（秒）
BUTTON_WAIT_TIMEOUT = 10  # ボタン表示待機タイムアウト（秒）
EXTENSION_LOAD_WAIT = 3  # 拡張機能読み込み待機時間（秒）

# Google Meet API スコープ
SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]

# Auto-Admit拡張機能のURL
AUTO_ADMIT_EXTENSION_URL = "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb"
AUTO_ADMIT_EXTENSION_ID = "epemkdedgaoeeobdjmkmhhhbjemckmgb"

# XPath定義
XPATH_JOIN_BUTTON = [
    "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/..",
    "//span[contains(text(), '参加') or contains(text(), 'Join')]/..",
    "//button[contains(@aria-label, '参加') or contains(@aria-label, 'Join')]",
]
XPATH_GEMINI_JOIN = (
    "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
)
XPATH_AUTO_ADMIT_BUTTON = [
    "//button[@aria-label='Toggle Auto-Admit']",
]

# Chrome Web Store XPath定義
XPATH_REMOVE_BUTTON = [
    "//span[contains(text(), 'Chrome から削除') or contains(text(), 'Remove from Chrome')]/..",
]
XPATH_ADD_BUTTON = [
    "//span[contains(text(), 'Chrome に追加') or contains(text(), 'Add to Chrome')]/..",
]


class GoogleMeetAutoHost:
    """Google Meetを自動でホストするクラス"""

    def __init__(self):
        self.driver: webdriver.Chrome | None = None
        self.meet_url: str | None = None
        self.creds: Credentials | None = None
        self.profile_dir = (
            Path(__file__).parent.parent.parent / ".chrome-profile-remote"
        )

    def create_meet_space(self) -> str:
        """Google Meet APIを使用して新しいMeetスペースを作成"""
        creds = None
        token_path = Path(__file__).parent.parent.parent / "token.json"
        credentials_path = Path(__file__).parent.parent.parent / "credentials.json"

        # トークンが存在する場合は読み込む
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # 認証が必要な場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    print(
                        "認証情報ファイル (credentials.json) が見つかりません。"
                        "Google Cloud Consoleからダウンロードしてください。"
                    )
                    sys.exit(1)
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            # 認証情報を保存
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        # 認証情報を保存（ログイン確認で使用）
        self.creds = creds

        # Meet APIクライアントを作成してスペースを作成
        try:
            client = meet_v2.SpacesServiceClient(credentials=creds)
            request = meet_v2.CreateSpaceRequest()
            response = client.create_space(request=request)
            meet_url = response.meeting_uri
            print(f"新しいMeetスペースを作成しました: {meet_url}")
            return meet_url
        except Exception as error:
            print(f"Meet APIエラー: {error}")
            raise

    def setup_driver(self):
        """Chromeドライバーの設定（拡張機能付き）"""
        options = Options()

        # プロファイルディレクトリを作成（拡張機能を永続化）
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--profile-directory=Default")

        # 言語設定を日本語に
        options.add_argument("--lang=ja")

        # メディアストリームの設定
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

        # その他のオプション
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # ウィンドウサイズ設定
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)

    def ensure_google_login(self):
        """Google Meet API認証と同じアカウントでログインを確認"""
        if not self.driver:
            return

        print("Googleアカウントへのログイン状態を確認しています...")

        # Googleアカウントページを開いてログイン状態を確認
        self.driver.get("https://myaccount.google.com/")
        time.sleep(3)

        # ログインしているかチェック
        try:
            # 現在ログインしているアカウントのメールアドレスを取得
            current_url = self.driver.current_url
            if "myaccount.google.com" in current_url and "signin" not in current_url:
                # アカウント情報を取得するためにMyAccountページに移動
                self.driver.get("https://myaccount.google.com/")
                time.sleep(3)

                # メタタグからログインしているメールアドレスを取得
                try:
                    meta_element = self.driver.find_element(
                        By.XPATH, "//meta[@name='og-profile-acct']"
                    )
                    current_email = meta_element.get_attribute("content")

                    if current_email and "@" in current_email:
                        print(f"現在ログイン中: {current_email}")
                        return True
                except Exception:
                    print("Googleアカウントにログイン済みです")
                    return True
        except Exception:
            pass

        # ログインしていない場合、ログインページに遷移
        print("Googleアカウントにログインしてください...")
        self.driver.get("https://accounts.google.com/signin")
        print("ブラウザでMeet APIで使用したGoogleアカウントにログインしてください。")
        print("ログイン完了後、Enterキーを押してください...")
        input("Enterキーを押してください: ")
        return True

    def install_extension_if_needed(self):
        """Auto-Admit拡張機能がインストールされていない場合はインストール"""
        if not self.driver:
            return

        print("Auto-Admit拡張機能のインストール状況を確認しています...")

        # 拡張機能のChrome Web Storeページを開く
        self.driver.get(AUTO_ADMIT_EXTENSION_URL)
        time.sleep(3)

        # 拡張機能が既にインストールされているか確認
        is_installed = False

        # 「Chromeから削除」ボタンがあるかチェック
        for xpath in XPATH_REMOVE_BUTTON:
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                is_installed = True
                break
            except TimeoutException:
                continue

        if is_installed:
            print("Auto-Admit拡張機能は既にインストールされています")
            return

        # インストールされていない場合、インストールを実行
        print("Auto-Admit拡張機能をインストールしています...")

        add_button = None
        for xpath in XPATH_ADD_BUTTON:
            try:
                add_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                break
            except TimeoutException:
                continue

        if add_button:
            add_button.click()
            print("「Chromeに追加」ボタンをクリックしました")

            # Chromeの拡張機能インストール確認ポップアップを処理
            try:
                # アラートダイアログを受け入れる
                alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                alert.accept()  # FIXME: うまく行かないので手動対応必要 → 一度行えばプロファイルに設定されるはず
                print("拡張機能のインストールを確認しました")

                # インストール完了まで待機
                time.sleep(3)
                print("Auto-Admit拡張機能のインストールが完了しました")

            except TimeoutException:
                print(
                    "確認ダイアログが見つかりませんでした。手動でインストールを完了してください。"
                )
                print(
                    "ブラウザで確認ダイアログが表示された場合は、「拡張機能を追加」をクリックしてください。"
                )
                input("インストール完了後、Enterキーを押してください: ")

        else:
            print("「Chromeに追加」ボタンが見つかりませんでした")
            print("手動で拡張機能をインストールしてください")
            input("インストール完了後、Enterキーを押してください: ")

    def join_meeting_as_host(self, meet_url: str):
        """Google Meetにホストとして参加"""
        if not self.driver:
            raise ValueError("ドライバーが初期化されていません")

        print(f"Meeting URLを開いています: {meet_url}")
        self.driver.get(meet_url)

        # ページ読み込み待機
        time.sleep(PAGE_LOAD_WAIT)

        # 「今すぐ参加」ボタンを探してクリック
        join_now_button = None
        for xpath in XPATH_JOIN_BUTTON:
            try:
                join_now_button = WebDriverWait(self.driver, BUTTON_WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                break
            except TimeoutException:
                continue

        if join_now_button:
            join_now_button.click()
            print("会議に参加しました")

            # Geminiメモ作成の確認ポップアップが出る場合の処理
            time.sleep(3)
            try:
                gemini_join_button = self.driver.find_element(
                    By.XPATH, XPATH_GEMINI_JOIN
                )
                gemini_join_button.click()
                print("Geminiメモ作成確認を処理しました")
            except Exception:
                pass
        else:
            print("参加ボタンが見つかりませんでした")
            raise TimeoutException("参加ボタンが見つかりませんでした")

    def enable_auto_admit(self):
        """Auto-Admit機能を有効化"""
        if not self.driver:
            raise ValueError("ドライバーが初期化されていません")

        print("Auto-Admit機能を有効化しています...")

        # 会議に完全に参加するまで待機
        time.sleep(5)

        # Auto-Admitボタンを探す
        auto_admit_button = None
        for xpath in XPATH_AUTO_ADMIT_BUTTON:
            try:
                auto_admit_button = WebDriverWait(
                    self.driver, BUTTON_WAIT_TIMEOUT
                ).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                break
            except TimeoutException:
                continue

        if auto_admit_button:
            # ボタンの状態を確認（aria-pressed属性）
            is_pressed = auto_admit_button.get_attribute("aria-pressed") == "true"

            if not is_pressed:
                # OFFの場合はクリックしてONにする
                auto_admit_button.click()
                print("Auto-Admit機能を有効にしました")
            else:
                print("Auto-Admit機能は既に有効です")
        else:
            print(
                "Auto-Admitボタンが見つかりませんでした。拡張機能が正しくインストールされているか確認してください。"
            )
            # 拡張機能の再インストールを試みる
            self.install_extension_if_needed()

    def run(self):
        """メイン処理"""
        try:
            # 1. Meet URLを生成
            self.meet_url = self.create_meet_space()

            # 2. Chromeドライバーをセットアップ
            self.setup_driver()

            # 3. Googleアカウントへのログインを確認
            self.ensure_google_login()

            # # 4. 拡張機能をインストール（必要な場合）
            self.install_extension_if_needed()

            # # 5. Meetに参加
            self.join_meeting_as_host(self.meet_url)

            # # 6. Auto-Admit機能を有効化
            self.enable_auto_admit()

            print(f"\n会議をホスト中です。Meet URL: {self.meet_url}")
            print("終了するにはCtrl+Cを押してください。")

            # 会議中は待機
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n終了します...")
        except Exception as e:
            print(f"エラー: {e}")
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """メイン処理"""
    host = GoogleMeetAutoHost()
    host.run()


if __name__ == "__main__":
    main()
