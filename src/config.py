"""
UI設定定数定義
日本語版Chrome前提で作成されたXPath・テキストを一元管理
"""


class Config:
    """UI要素設定の統一アクセスポイント"""

    class GoogleMeet:
        """Google Meet関連の設定"""

        # XPath定数
        JOIN_BUTTON_XPATH: str = (
            "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
        )
        NAME_INPUT_XPATH: str = (
            "//input[@placeholder='名前' or @placeholder='Your name']"
        )
        REQUEST_JOIN_BUTTON_XPATH: str = "//span[contains(text(), '参加をリクエスト') or contains(text(), 'Ask to join')]/.."
        GEMINI_JOIN_BUTTON_XPATH: str = (
            "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
        )
        LEAVE_BUTTON_XPATH: str = (
            "//button[@aria-label='通話から退出' or @aria-label='Leave call']"
        )
        AUTO_ADMIT_BUTTON_XPATH: str = "//button[@aria-label='Toggle Auto-Admit']"

        # ナビゲーション関連テキスト
        HOME_BUTTON_TEXT: str = "ホーム画面に戻る"

    class ChromeExtension:
        """Chrome拡張機能関連の設定"""

        # XPath定数
        REMOVE_BUTTON_XPATH: str = "//span[contains(text(), 'Chrome から削除') or contains(text(), 'Remove from Chrome')]/.."
        ADD_BUTTON_XPATH: str = "//span[contains(text(), 'Chrome に追加') or contains(text(), 'Add to Chrome')]/.."
