"""
UI設定定数定義
日本語版Chrome前提で作成されたXPath・テキストを一元管理
"""


class Config:
    """UI要素設定の統一アクセスポイント"""

    class GoogleMeet:
        """Google Meet関連の設定"""

        # XPath定数
        JOIN_BUTTON_XPATH: str = "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
        NAME_INPUT_XPATH: str = "//input[@placeholder='名前' or @placeholder='Your name']"
        REQUEST_JOIN_BUTTON_XPATH: str = "//span[contains(text(), '参加をリクエスト') or contains(text(), 'Ask to join')]/.."
        GEMINI_JOIN_BUTTON_XPATH: str = "//span[contains(text(), '今すぐ参加') or contains(text(), 'Join now')]/.."
        LEAVE_BUTTON_XPATH: str = "//button[@aria-label='通話から退出' or @aria-label='Leave call']"
        AUTO_ADMIT_BUTTON_XPATH: str = "//button[@aria-label='Toggle Auto-Admit']"
        EXTENSION_ENABLE_BUTTON_XPATH: str = "//span[contains(text(), '今すぐ有効にする') or contains(text(), 'Enable now')]/.."

        # テキスト定数
        JOIN_NOW_TEXT: str = "今すぐ参加"
        LEAVE_CALL_TEXT: str = "通話から退出"
        REQUEST_JOIN_TEXT: str = "参加をリクエスト"
        ENABLE_NOW_TEXT: str = "今すぐ有効にする"

        # ナビゲーション関連テキスト
        HOME_BUTTON_TEXT: str = "ホーム画面に戻る"
        BACK_BUTTON_TEXT: str = "戻る"
        CLOSE_BUTTON_TEXT: str = "閉じる"
        CANCEL_BUTTON_TEXT: str = "キャンセル"
        OK_BUTTON_TEXT: str = "OK"
        CONFIRM_BUTTON_TEXT: str = "確認"

    class ChromeExtension:
        """Chrome拡張機能関連の設定"""

        # XPath定数
        REMOVE_BUTTON_XPATH: str = "//span[contains(text(), 'Chrome から削除') or contains(text(), 'Remove from Chrome')]/.."
        ADD_BUTTON_XPATH: str = "//span[contains(text(), 'Chrome に追加') or contains(text(), 'Add to Chrome')]/.."

        # テキスト定数
        ADD_TO_CHROME_TEXT: str = "Chrome に追加"
        REMOVE_FROM_CHROME_TEXT: str = "Chrome から削除"


# 使用箇所マッピング（ドキュメント用）
XPATH_USAGE_MAP = {
    "Config.GoogleMeet.JOIN_BUTTON_XPATH": [
        "src/remote/meet_manager.py:MeetManager.join_as_host",
        "src/front/meet_participant.py:MeetParticipant._join_as_guest"
    ],
    "Config.GoogleMeet.NAME_INPUT_XPATH": [
        "src/front/meet_participant.py:MeetParticipant._join_as_guest"
    ],
    "Config.GoogleMeet.REQUEST_JOIN_BUTTON_XPATH": [
        "src/front/meet_participant.py:MeetParticipant._join_as_guest"
    ],
    "Config.GoogleMeet.GEMINI_JOIN_BUTTON_XPATH": [
        "src/front/meet_participant.py:MeetParticipant._handle_gemini_popup"
    ],
    "Config.GoogleMeet.LEAVE_BUTTON_XPATH": [
        "src/front/meet_participant.py:MeetParticipant.leave_meeting",
        "src/front/meet_participant.py:MeetParticipant.is_in_meeting"
    ],
    "Config.GoogleMeet.AUTO_ADMIT_BUTTON_XPATH": [
        "src/remote/meet_manager.py:MeetManager.enable_auto_admit"
    ],
    "Config.ChromeExtension.REMOVE_BUTTON_XPATH": [
        "src/remote/meet_manager.py:MeetManager.check_extension"
    ],
    "Config.ChromeExtension.ADD_BUTTON_XPATH": [
        "src/remote/meet_manager.py:MeetManager.check_extension"
    ]
}
