#!/usr/bin/env python3
"""
Google Meet自動入室スクリプト（フロントPC用）
ターミナルでMeetリンクを受け取り、ブラウザで開いて自動入室する
"""

import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 定数定義
PAGE_LOAD_WAIT = 3  # ページ読み込み待機時間（秒）
BUTTON_WAIT_TIMEOUT = 10  # ボタン表示待機タイムアウト（秒）
POPUP_WAIT = 10  # ポップアップ表示待機時間（秒）

# XPath定義
XPATH_JOIN_BUTTON = (
    "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/..|"
    "//span[contains(text(), '参加') or contains(text(), 'Join')]/..|"
    "//button[contains(@aria-label, '参加') or contains(@aria-label, 'Join')]"
)
XPATH_NAME_INPUT = "//input[@placeholder='名前' or @placeholder='Your name']"
XPATH_REQUEST_JOIN = (
    "//span[contains(text(), '参加をリクエスト') or contains(text(), 'Ask to join')]/.."
)
XPATH_GEMINI_JOIN = (
    "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
)
XPATH_LEAVE_BUTTON = "//button[@aria-label='通話から退出' or @aria-label='Leave call']"


class GoogleMeetAutoJoiner:
    """Google Meetに自動で入室するクラス"""

    def __init__(self, use_profile: bool = True):
        self.use_profile = use_profile
        self.driver: webdriver.Chrome | None = None

    def setup_driver(self):
        """Chromeドライバーの設定"""
        options = Options()

        # ユーザープロファイルの設定（ログイン状態を保持）
        if self.use_profile:
            # プロファイルディレクトリを作成
            profile_dir = Path(__file__).parent.parent.parent / ".chrome-profile-front"
            profile_dir.mkdir(parents=True, exist_ok=True)

            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument("--profile-directory=Default")

        # 言語設定を日本語に
        options.add_argument("--lang=ja")

        # メディアストリームの設定
        options.add_experimental_option(
            "prefs",  # cspell:ignore prefs
            {
                "intl.accept_languages": "ja,en-US,en",
                "profile.default_content_setting_values.media_stream_mic": 1,
                "profile.default_content_setting_values.media_stream_camera": 1,
                "profile.default_content_setting_values.geolocation": 0,
                "profile.default_content_setting_values.notifications": 2,
            },
        )

        # その他のオプション
        options.add_argument(
            "--use-fake-ui-for-media-stream"
        )  # メディアストリームの確認をスキップ
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # ウィンドウサイズ設定
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)

    def validate_meet_url(self, url: str) -> bool:
        """Google MeetのURLかどうかを検証"""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ["meet.google.com"]
        except Exception:
            return False

    def join_meeting(self, meet_url: str, display_name: str = "Reception"):
        """Google Meetに自動入室"""
        if not self.validate_meet_url(meet_url):
            raise ValueError(f"無効なGoogle Meet URL: {meet_url}")

        # ドライバーのセットアップ
        self.setup_driver()

        if self.driver is None:
            raise ValueError("ドライバーのセットアップに失敗しました")

        print(f"Meeting URLを開いています: {meet_url}")
        self.driver.get(meet_url)

        # ページ読み込み待機
        time.sleep(PAGE_LOAD_WAIT)

        # 名前入力フィールドを探す（ゲストとして参加する場合）
        # 英語・日本語両方のUIに対応
        try:
            if self.use_profile:
                # ログイン済みの場合は直接参加
                print("ログイン済みユーザーとして参加を試みます")

                # 「今すぐ参加」ボタンを探してクリック
                try:
                    join_now_button = WebDriverWait(
                        self.driver, BUTTON_WAIT_TIMEOUT
                    ).until(EC.element_to_be_clickable((By.XPATH, XPATH_JOIN_BUTTON)))
                    join_now_button.click()
                    print("会議に参加しました")

                    # Geminiメモ作成の確認ポップアップが出る場合の処理
                    time.sleep(POPUP_WAIT)
                    try:
                        # ポップアップ内の「今すぐ参加」ボタンを探す
                        gemini_join_button = self.driver.find_element(
                            By.XPATH, XPATH_GEMINI_JOIN
                        )
                        gemini_join_button.click()
                        print("Geminiメモ作成確認を処理しました")
                    except Exception:
                        # ポップアップが出ない場合は何もしない
                        pass

                except TimeoutException:
                    print("参加ボタンが見つかりませんでした")
            else:
                print("ゲストとして参加を試みます")

                name_input = WebDriverWait(self.driver, BUTTON_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, XPATH_NAME_INPUT))
                )
                name_input.clear()
                name_input.send_keys(display_name)
                print(f"表示名を入力しました: {display_name}")

                # 「参加をリクエスト」または「Ask to join」ボタンをクリック
                join_button = self.driver.find_element(By.XPATH, XPATH_REQUEST_JOIN)
                join_button.click()
                print("参加をリクエストしました")

                # Geminiメモ作成の確認ポップアップが出る場合の処理（ゲストの場合も）
                time.sleep(POPUP_WAIT)
                try:
                    # ポップアップ内の「今すぐ参加」ボタンを探す
                    gemini_join_button = self.driver.find_element(
                        By.XPATH, XPATH_GEMINI_JOIN
                    )
                    gemini_join_button.click()
                    print("Geminiメモ作成確認を処理しました")
                except:
                    # ポップアップが出ない場合は何もしない
                    pass

        except TimeoutException:
            print("参加ボタンが見つかりませんでした")
            raise

        # 参加成功の確認
        print("Google Meetへの入室が完了しました")

    def leave_meeting(self):
        """会議から退出"""
        if not self.driver:
            return

        try:
            # 通話を終了ボタンをクリック
            try:
                leave_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, XPATH_LEAVE_BUTTON))
                )
                leave_button.click()
                print("会議から退出しました")
                # クリック後、少し待機
                time.sleep(2)
            except TimeoutException:
                print("退出ボタンが見つかりませんでした")
            except Exception as e:
                print(f"退出エラー: {e}")
        except Exception as e:
            print(f"退出処理中にエラーが発生しました: {e}")
        finally:
            # ドライバーを安全に終了
            try:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
            except Exception as e:
                print(f"ドライバー終了エラー: {e}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python google_meet_auto_join.py <Google Meet URL> [表示名] [--no-profile]"
        )
        print("\nオプション:")
        print("  --no-profile  プロファイルを使用せず、ゲストとして参加")
        sys.exit(1)

    meet_url = sys.argv[1]
    display_name = "Reception"
    use_profile = True

    # 引数の解析
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == "--no-profile":
            use_profile = False
        else:
            display_name = sys.argv[i]

    joiner = GoogleMeetAutoJoiner(use_profile=use_profile)

    try:
        joiner.join_meeting(meet_url, display_name)

        # 会議中は待機（Ctrl+Cで終了）
        print("\n会議に参加中です。終了するにはCtrl+Cを押してください。")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n終了します...")
        joiner.leave_meeting()
    except Exception as e:
        print(f"エラー: {e}")
        joiner.leave_meeting()
        sys.exit(1)


if __name__ == "__main__":
    main()
