"""
リモートPC用FletベースGUI
VTube Studio制御と接続管理を提供
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime

import flet as ft
from flet.core.colors import Colors
from flet.core.icons import Icons

from ..models.enums import ConnectionStatus
from ..models.schemas import GUIState
from ..utils.platform_utils import PlatformUtils

logger = logging.getLogger(__name__)


class RemoteGUI:
    """リモートPC用のFletベースGUI"""

    def __init__(self):
        # 状態管理
        self.state = GUIState(status=ConnectionStatus.WAITING)
        self._running = False
        self._connect_callback: Callable[[str], None] | None = None
        self._disconnect_callback: Callable[[], None] | None = None

        # Fletコンポーネント
        self.page: ft.Page | None = None
        self.status_text: ft.Text | None = None
        self.target_input: ft.TextField | None = None
        self.connect_button: ft.FilledButton | None = None
        self.disconnect_button: ft.FilledButton | None = None
        self.log_column: ft.Column | None = None
        self.log_container: ft.Container | None = None
        self.vtube_status_text: ft.Text | None = None

        # Chrome拡張機能個別ステータス
        self.auto_admit_status: ft.Text | None = None
        self.auto_admit_button: ft.OutlinedButton | None = None
        self.screen_capture_status: ft.Text | None = None
        self.screen_capture_button: ft.OutlinedButton | None = None
        self.google_login_status: ft.Text | None = None
        self.google_login_button: ft.OutlinedButton | None = None

        # チェック状態
        self.check_states = {
            "auto_admit": False,
            "screen_capture": False,
            "google_login": False,
        }

    def setup_page(self, page: ft.Page) -> None:
        """ページの初期設定"""
        self.page = page
        page.title = "VTuber受付システム - リモートPC"
        page.window.width = 800
        page.window.height = 700
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 20

        # ヘッダー
        header = ft.Container(
            content=ft.Text(
                "VTuber受付システム - リモートPC",
                size=24,
                weight=ft.FontWeight.BOLD,
                color=Colors.PRIMARY,
            ),
            margin=ft.margin.only(bottom=20),
        )

        # 接続設定カード
        self.target_input = ft.TextField(
            label="接続先（IPアドレスまたはデバイス名）",
            value="",
            hint_text="例: 192.168.1.100 または front-pc",
            border_radius=8,
            filled=True,
            expand=True,
        )

        self.connect_button = ft.FilledButton(
            text="接続",
            icon=Icons.CONNECT_WITHOUT_CONTACT,
            on_click=self._on_connect,
            disabled=True,  # 初期状態では無効化（チェック完了後に有効化）
        )

        self.disconnect_button = ft.FilledButton(
            text="切断",
            icon=Icons.LINK_OFF,
            on_click=self._on_disconnect,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor=Colors.ERROR,
            ),
        )

        connection_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("接続設定", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=1),
                        ft.Row(
                            [
                                self.target_input,
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                self.connect_button,
                                self.disconnect_button,
                            ],
                            spacing=10,
                        ),
                    ]
                ),
                padding=20,
            ),
            elevation=2,
        )

        # ステータスカード
        self.status_text = ft.Text(
            self.state.status.value,
            size=16,
            weight=ft.FontWeight.W_500,
            color=self._get_status_color(self.state.status),
        )

        # アプリケーションステータス
        self.vtube_status_text = ft.Text(
            "起動前",
            size=14,
            color=Colors.SECONDARY,
        )

        # Chrome拡張機能個別ステータス
        self.auto_admit_status = ft.Text(
            "チェック中...",
            size=12,
            color=Colors.SECONDARY,
        )

        self.auto_admit_button = ft.OutlinedButton(
            text="インストール",
            icon=Icons.DOWNLOAD,
            visible=False,
            on_click=lambda _: self._open_extension_page("auto_admit"),
            height=30,
        )

        self.screen_capture_status = ft.Text(
            "チェック中...",
            size=12,
            color=Colors.SECONDARY,
        )

        self.screen_capture_button = ft.OutlinedButton(
            text="インストール",
            icon=Icons.DOWNLOAD,
            visible=False,
            on_click=lambda _: self._open_extension_page("screen_capture"),
            height=30,
        )

        self.google_login_status = ft.Text(
            "チェック中...",
            size=12,
            color=Colors.SECONDARY,
        )

        self.google_login_button = ft.OutlinedButton(
            text="ログイン",
            icon=Icons.LOGIN,
            visible=False,
            on_click=lambda _: self._open_google_login(),
            height=30,
        )

        status_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("システム状態", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=1),
                        ft.Row(
                            [
                                ft.Text("接続状態:", size=14),
                                self.status_text,
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Text("VTube Studio:", size=14),
                                self.vtube_status_text,
                            ]
                        ),
                        ft.Row([ft.Text("Chrome:", size=14)]),
                        # Chrome拡張機能の詳細ステータス（インデント表示）
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(
                                                "  • Auto-Admit:",
                                                size=12,
                                                color=Colors.SECONDARY,
                                            ),
                                            self.auto_admit_status,
                                            self.auto_admit_button,
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text(
                                                "  • Screen Capture:",
                                                size=12,
                                                color=Colors.SECONDARY,
                                            ),
                                            self.screen_capture_status,
                                            self.screen_capture_button,
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text(
                                                "  • Google Login:",
                                                size=12,
                                                color=Colors.SECONDARY,
                                            ),
                                            self.google_login_status,
                                            self.google_login_button,
                                        ],
                                        spacing=10,
                                    ),
                                ],
                                spacing=5,
                            ),
                            margin=ft.margin.only(left=20),
                        ),
                        ft.Row(
                            [
                                ft.Text("プラットフォーム:", size=14),
                                ft.Text(
                                    PlatformUtils.get_platform().value.capitalize(),
                                    size=14,
                                    color=Colors.SECONDARY,
                                ),
                            ]
                        ),
                    ]
                ),
                padding=20,
            ),
            elevation=2,
        )

        # ログエリア
        self.log_column = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=5,
        )

        self.log_container = ft.Container(
            content=self.log_column,
            bgcolor="#1a1a1a",
            border_radius=8,
            padding=10,
            height=350,
            expand=True,
        )

        log_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("ログ", size=18, weight=ft.FontWeight.BOLD),
                                ft.IconButton(
                                    icon=Icons.CLEAR_ALL,
                                    tooltip="ログをクリア",
                                    on_click=self._clear_log,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=1),
                        self.log_container,
                    ],
                    expand=True,
                ),
                padding=20,
            ),
            elevation=2,
            expand=True,
        )

        # ボタンエリア
        button_row = ft.Row(
            [
                ft.FilledButton(
                    text="終了",
                    icon=Icons.CLOSE,
                    on_click=self._on_exit,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        # レイアウト構築
        page.add(
            ft.Column(
                [
                    header,
                    connection_card,
                    status_card,
                    log_card,
                    button_row,
                ],
                expand=True,
            )
        )

        # 初期ログ
        self.add_log("システムを起動しました")
        self.add_log(f"プラットフォーム: {PlatformUtils.get_platform().value}")

        # バックグラウンドでシステムチェックを開始
        self._run_background_checks()

    def _get_status_color(self, status: ConnectionStatus) -> str:
        """ステータスに応じた色を取得"""
        color_map = {
            ConnectionStatus.WAITING: Colors.ORANGE,
            ConnectionStatus.CONNECTING: Colors.BLUE,
            ConnectionStatus.CONNECTED: Colors.GREEN,
            ConnectionStatus.ERROR: Colors.RED,
            ConnectionStatus.DISCONNECTING: Colors.ORANGE,
        }
        return color_map.get(status, Colors.PRIMARY)

    def update_status(self, status_enum: ConnectionStatus) -> None:
        """接続ステータスの更新"""
        try:
            self.state.status = status_enum

            if self.page and self.status_text:
                self.status_text.value = status_enum.value
                self.status_text.color = self._get_status_color(status_enum)

                # ボタンの有効/無効を更新
                if status_enum == ConnectionStatus.CONNECTED:
                    if self.connect_button:
                        self.connect_button.disabled = True
                    if self.disconnect_button:
                        self.disconnect_button.disabled = False
                else:
                    if self.connect_button:
                        self.connect_button.disabled = False
                    if self.disconnect_button:
                        self.disconnect_button.disabled = True

                self.page.update()
        except Exception as e:
            logger.error(f"ステータス更新エラー: {e}")

    def update_app_status(self, app_name: str, status: str) -> None:
        """アプリケーションステータスの更新"""
        if self.page:
            if app_name.lower() == "vtube studio":
                if self.vtube_status_text:
                    self.vtube_status_text.value = status
                    self.vtube_status_text.color = (
                        Colors.GREEN if status == "起動中" else Colors.SECONDARY
                    )

            self.page.update()

    def add_log(self, message: str) -> None:
        """ログメッセージの追加"""
        if self.page and self.log_column:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = ft.Container(
                content=ft.Row(
                    [
                        ft.Text(f"[{timestamp}]", size=12, color=Colors.SECONDARY),
                        ft.Text(message, size=12, expand=True),
                    ],
                    spacing=10,
                ),
                padding=ft.padding.symmetric(horizontal=5, vertical=2),
            )

            self.log_column.controls.append(log_entry)

            # 最大ログ数を制限
            if len(self.log_column.controls) > 100:
                self.log_column.controls.pop(0)

            self.page.update()

            # 最下部にスクロール（可能な場合のみ）
            if self.log_container and hasattr(self.log_container, "scroll_to"):
                try:
                    self.log_container.scroll_to(  # type: ignore
                        offset=-1,
                        duration=100,
                    )
                except Exception:
                    # scroll_toが利用できない場合は無視
                    pass

    def _clear_log(self, _e) -> None:
        """ログをクリア"""
        if self.log_column:
            self.log_column.controls.clear()
            self.add_log("ログをクリアしました")

    def _on_connect(self, _e) -> None:
        """接続ボタンのハンドラ（最小限の動作）"""
        if self.target_input and self._connect_callback:
            target = self.target_input.value.strip()
            if target:
                self.add_log(f"接続先: {target}")
                self._connect_callback(target)
            else:
                self.add_log("エラー: 接続先を入力してください")

    def _on_disconnect(self, _e) -> None:
        """切断ボタンのハンドラ"""
        if self._disconnect_callback:
            self._disconnect_callback()

    def _open_extension_page(self, extension_type: str) -> None:
        """拡張機能のインストールページを開く"""
        from src.remote.prechecks import PrecheckManager

        urls = {
            "auto_admit": "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb",
            "screen_capture": "https://chromewebstore.google.com/detail/screen-capture-virtual-ca/jcnomcmilppjoogdhhnadpcabpdlikmc",
        }

        if extension_type in urls:
            try:
                # PrecheckManagerを使って既存のプロファイルでChromeを開く
                manager = PrecheckManager()
                manager._setup_browser(headless=False)
                if manager.driver:
                    manager.driver.get(urls[extension_type])
                    self.add_log(f"{extension_type}の拡張機能ページを開きました")
                else:
                    self.add_log("エラー: ブラウザの起動に失敗しました")
            except Exception as e:
                self.add_log(f"エラー: {str(e)}")

    def _open_google_login(self) -> None:
        """Googleログインページを開く"""
        from src.remote.prechecks import PrecheckManager

        try:
            # PrecheckManagerを使って既存のプロファイルでChromeを開く
            manager = PrecheckManager()
            manager._setup_browser(headless=False)
            if manager.driver:
                manager.driver.get("https://accounts.google.com/")
                self.add_log("Googleログインページを開きました")
            else:
                self.add_log("エラー: ブラウザの起動に失敗しました")
        except Exception as e:
            self.add_log(f"エラー: {str(e)}")

    def _run_background_checks(self) -> None:
        """バックグラウンドで事前チェックを実行"""
        import threading

        from src.remote.prechecks import PrecheckManager

        def check_thread():
            try:
                # チェック開始時は接続ボタンを無効化
                if self.page and self.connect_button:
                    self.connect_button.disabled = True
                    self.page.update()

                # VTube Studioの状態チェック
                from src.utils.vtube_studio_utils import check_and_setup_vtube_studio

                vtube_ok, vtube_message = check_and_setup_vtube_studio()
                if self.page and self.vtube_status_text:
                    self.vtube_status_text.value = "起動中" if vtube_ok else "起動前"
                    self.vtube_status_text.color = (
                        Colors.GREEN if vtube_ok else Colors.SECONDARY
                    )
                    self.page.update()
                if vtube_ok:
                    self.add_log(f"VTube Studio: {vtube_message}")

                self.add_log("システムチェックを開始しています...")

                # PrecheckManagerのインスタンスを作成
                manager = PrecheckManager()

                # 各チェックを個別に実行
                # Auto-Admitチェック
                try:
                    result = manager.check_extension(
                        "https://chromewebstore.google.com/detail/auto-admit-for-google-mee/epemkdedgaoeeobdjmkmhhhbjemckmgb",
                        "Auto-Admit",
                    )
                    self.check_states["auto_admit"] = result
                    if self.page:
                        self.auto_admit_status.value = (
                            "✓ インストール済み" if result else "✗ 未インストール"
                        )
                        self.auto_admit_status.color = (
                            Colors.GREEN if result else Colors.ERROR
                        )
                        self.auto_admit_button.visible = not result
                        self.page.update()
                except Exception as e:
                    self.add_log(f"Auto-Admitチェックエラー: {str(e)}")
                    if self.page:
                        self.auto_admit_status.value = "✗ チェック失敗"
                        self.auto_admit_status.color = Colors.ERROR
                        self.auto_admit_button.visible = True
                        self.page.update()

                # Screen Captureチェック
                try:
                    result = manager.check_extension(
                        "https://chromewebstore.google.com/detail/screen-capture-virtual-ca/jcnomcmilppjoogdhhnadpcabpdlikmc",
                        "Screen Capture",
                    )
                    self.check_states["screen_capture"] = result
                    if self.page:
                        self.screen_capture_status.value = (
                            "✓ インストール済み" if result else "✗ 未インストール"
                        )
                        self.screen_capture_status.color = (
                            Colors.GREEN if result else Colors.ERROR
                        )
                        self.screen_capture_button.visible = not result
                        self.page.update()
                except Exception as e:
                    self.add_log(f"Screen Captureチェックエラー: {str(e)}")
                    if self.page:
                        self.screen_capture_status.value = "✗ チェック失敗"
                        self.screen_capture_status.color = Colors.ERROR
                        self.screen_capture_button.visible = True
                        self.page.update()

                # Googleログインチェック
                try:
                    # _check_google_loginは非同期メソッドではないので直接呼び出し
                    result = manager.check_google_login()
                    self.check_states["google_login"] = result
                    if self.page:
                        self.google_login_status.value = (
                            "✓ ログイン済み" if result else "✗ 未ログイン"
                        )
                        self.google_login_status.color = (
                            Colors.GREEN if result else Colors.ERROR
                        )
                        self.google_login_button.visible = not result
                        self.page.update()
                except Exception as e:
                    self.add_log(f"Googleログインチェックエラー: {str(e)}")
                    if self.page:
                        self.google_login_status.value = "✗ チェック失敗"
                        self.google_login_status.color = Colors.ERROR
                        self.google_login_button.visible = True
                        self.page.update()

                # すべてのチェック完了
                all_passed = all(self.check_states.values())
                if all_passed:
                    self.add_log("✓ すべてのシステムチェックが完了しました")
                    # すべてOKなら接続ボタンを有効化
                    if self.page and self.connect_button:
                        self.connect_button.disabled = False
                        self.page.update()
                else:
                    failed_items = [k for k, v in self.check_states.items() if not v]
                    self.add_log(
                        f"⚠ 一部のチェックが失敗しました: {', '.join(failed_items)}"
                    )
                    # 失敗がある場合は接続ボタンを無効のまま
                    if self.page and self.connect_button:
                        self.connect_button.disabled = True
                        self.page.update()

            except Exception as e:
                self.add_log(f"バックグラウンドチェックエラー: {str(e)}")

        # バックグラウンドスレッドで実行
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def _on_exit(self, _e) -> None:
        """終了ボタンのハンドラ"""
        self.stop()

    def set_connect_callback(self, callback: Callable[[str], None]) -> None:
        """接続時のコールバックを設定"""
        self._connect_callback = callback

    def set_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """切断時のコールバックを設定"""
        self._disconnect_callback = callback

    def run(self) -> None:
        """GUIを実行"""
        self._running = True

        def main(page: ft.Page):
            self.setup_page(page)

        ft.app(target=main)

    def stop(self) -> None:
        """GUIの停止"""
        self._running = False
        if self.page:
            self.page.window.close()


def run_gui(
    connect_callback: Callable[[str], None] | None = None,
    disconnect_callback: Callable[[], None] | None = None,
) -> RemoteGUI:
    """GUI をバックグラウンドスレッドで実行"""
    gui = RemoteGUI()
    if connect_callback:
        gui.set_connect_callback(connect_callback)
    if disconnect_callback:
        gui.set_disconnect_callback(disconnect_callback)

    thread = threading.Thread(target=gui.run, daemon=True)
    thread.start()

    # GUIの初期化を待つ
    time.sleep(0.5)

    return gui
