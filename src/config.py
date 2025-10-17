"""UI設定定数定義

日本語版Chrome前提で作成されたXPath・テキストを一元管理
"""

from pathlib import Path


class Config:
    """UI要素設定の統一アクセスポイント"""

    class GoogleMeet:
        """Google Meet関連の設定"""

        # XPath定数
        JOIN_BUTTON_XPATH: str = "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
        NAME_INPUT_XPATH: str = "//input[@placeholder='名前' or @placeholder='Your name']"
        REQUEST_JOIN_BUTTON_XPATH: str = (
            "//span[contains(text(), '参加をリクエスト') or contains(text(), 'Ask to join')]/.."
        )
        GEMINI_JOIN_BUTTON_XPATH: str = "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
        LEAVE_BUTTON_XPATH: str = "//button[@aria-label='通話から退出' or @aria-label='Leave call']"
        AUTO_ADMIT_BUTTON_XPATH: str = "//button[@aria-label='Toggle Auto-Admit']"
        SECURITY_DIALOG_CLOSE_BUTTON_XPATH: str = (
            "//button[contains(@class, 'UywwFc-LgbsSe') and "
            ".//span[contains(text(), '閉じる') or contains(text(), 'Close')]]"
        )

        # 待機時間設定（秒）
        PAGE_LOAD_WAIT: float = 1.5  # ページ読み込み待機時間
        SECURITY_DIALOG_WAIT: float = 10.0  # セキュリティダイアログ表示待機時間
        JOIN_COMPLETE_WAIT: float = 1.5  # Meet参加完了後の待機時間（＝auto admit有効化待機時間）
        PROCESS_MONITOR_INTERVAL: float = 2.0  # プロセス監視間隔
        PROCESS_MONITOR_ERROR_WAIT: float = 5.0  # プロセス監視エラー時の待機時間
        GEMINI_POPUP_CHECK_INTERVAL: float = 0.5  # Geminiポップアップチェック間隔

        # タイムアウト設定（秒）
        BUTTON_WAIT_TIMEOUT: int = 15  # ボタン検出のタイムアウト
        GEMINI_POPUP_WAIT: int = 90  # Geminiポップアップ最大待機時間

        # リトライ設定
        RETRY_MAX_ATTEMPTS: int = 3  # 最大リトライ回数
        RETRY_WAIT_SECONDS: float = 3.0  # リトライ間隔（秒）

        # ナビゲーション関連テキスト
        HOME_BUTTON_TEXT: str = "ホーム画面に戻る"

    class ChromeExtension:
        """Chrome拡張機能関連の設定"""

        # XPath定数
        REMOVE_BUTTON_XPATH: str = (
            "//span[contains(text(), 'Chrome から削除') or contains(text(), 'Remove from Chrome')]/.."
        )
        ADD_BUTTON_XPATH: str = "//span[contains(text(), 'Chrome に追加') or contains(text(), 'Add to Chrome')]/.."

    class VTubeStudio:
        """VTube Studio関連の設定"""

        # 待機時間設定（秒）
        LAUNCH_WAIT: float = 3.0  # VTube Studio起動後の待機時間
        STATUS_CHECK_INTERVAL: float = 1.0  # ステータスチェック間隔

    class Communication:
        """TCP通信関連の設定"""

        # 接続設定
        HOST: str = "localhost"  # デフォルトホスト
        PORT: int = 9999  # デフォルトポート
        TIMEOUT: float = 10.0  # ソケットタイムアウト（秒）

        # ハートビート設定
        HEARTBEAT_INTERVAL: float = 20.0  # ハートビート送信間隔（秒）
        HEARTBEAT_MAX_FAILURES: int = 3  # 最大連続失敗回数

    CONFIG_DIR: Path = Path.home() / ".planning-reception-avatar"


Config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
