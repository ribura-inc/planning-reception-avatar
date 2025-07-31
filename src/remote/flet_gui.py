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
from ..models.schemas import GUIState, RemoteSettings
from ..utils.platform_utils import PlatformUtils

logger = logging.getLogger(__name__)


class RemoteGUI:
    """リモートPC用のFletベースGUI"""

    def __init__(self):
        # 状態管理
        self.state = GUIState(status=ConnectionStatus.WAITING)
        self.settings = RemoteSettings()
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
        self.chrome_status_text: ft.Text | None = None

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
            value=self.settings.last_connected_device or "",
            hint_text="例: 192.168.1.100 または front-pc",
            border_radius=8,
            filled=True,
            expand=True,
        )

        self.connect_button = ft.FilledButton(
            text="接続",
            icon=Icons.CONNECT_WITHOUT_CONTACT,
            on_click=self._on_connect,
            disabled=False,
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

        self.chrome_status_text = ft.Text(
            "起動前",
            size=14,
            color=Colors.SECONDARY,
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
                        ft.Row(
                            [
                                ft.Text("Chrome:", size=14),
                                self.chrome_status_text,
                            ]
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
            bgcolor=Colors.ON_SURFACE_VARIANT,
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
                ft.OutlinedButton(
                    text="設定",
                    icon=Icons.SETTINGS,
                    on_click=self._on_settings,
                ),
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

    def update_status(self, status: str) -> None:
        """接続ステータスの更新"""
        try:
            # Enumに変換
            if status in [s.value for s in ConnectionStatus]:
                status_enum = ConnectionStatus(status)
            else:
                logger.warning(f"Unknown status: {status}")
                return

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
            elif app_name.lower() == "chrome" and self.chrome_status_text:
                self.chrome_status_text.value = status
                self.chrome_status_text.color = (
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

    def _clear_log(self, e) -> None:
        """ログをクリア"""
        if self.log_column:
            self.log_column.controls.clear()
            self.add_log("ログをクリアしました")

    def _on_connect(self, e) -> None:
        """接続ボタンのハンドラ"""
        if self.target_input and self._connect_callback:
            target = self.target_input.value.strip()
            if target:
                self.add_log(f"接続先: {target}")
                self._connect_callback(target)
                # 最後の接続先を保存
                self.settings.last_connected_device = target
            else:
                self.add_log("エラー: 接続先を入力してください")

    def _on_disconnect(self, e) -> None:
        """切断ボタンのハンドラ"""
        if self._disconnect_callback:
            self._disconnect_callback()

    def _on_settings(self, e) -> None:
        """設定ボタンのハンドラ"""

        # 設定ダイアログを表示
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def save_settings(e):
            # 設定を保存
            self.settings.skip_extension_check = skip_extension_check.value
            self.settings.skip_account_check = skip_account_check.value
            self.add_log("設定を保存しました")
            close_dialog(e)

        skip_extension_check = ft.Switch(
            label="拡張機能チェックをスキップ",
            value=self.settings.skip_extension_check,
        )

        skip_account_check = ft.Switch(
            label="Googleアカウントチェックをスキップ",
            value=self.settings.skip_account_check,
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("設定"),
            content=ft.Column(
                [
                    skip_extension_check,
                    skip_account_check,
                ],
                height=100,
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.FilledButton("保存", on_click=save_settings),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if hasattr(self.page, "dialog"):
            self.page.dialog = dialog  # type: ignore
            dialog.open = True
            self.page.update()
        else:
            # dialogがサポートされていない場合の代替処理
            self.add_log("設定ダイアログは現在のFletバージョンでサポートされていません")

    def _on_exit(self, e) -> None:
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


if __name__ == "__main__":
    # テスト実行
    gui = RemoteGUI()

    # テスト用のコールバック
    def on_connect(target: str):
        gui.add_log(f"接続処理を開始: {target}")
        gui.update_status(ConnectionStatus.CONNECTING.value)

        # 非同期でステータス更新をシミュレート
        def simulate_connection():
            time.sleep(1)
            gui.update_app_status("VTube Studio", "起動中")
            gui.add_log("VTube Studioを起動しました")

            time.sleep(1)
            gui.update_status(ConnectionStatus.CONNECTED.value)
            gui.add_log("フロントPCに接続しました")

            time.sleep(1)
            gui.update_app_status("Chrome", "起動中")
            gui.add_log("Chromeを起動しました")
            gui.add_log("Google Meetに参加しました")

        thread = threading.Thread(target=simulate_connection, daemon=True)
        thread.start()

    def on_disconnect():
        gui.add_log("切断処理を開始")
        gui.update_status(ConnectionStatus.DISCONNECTING.value)

        # 非同期で切断をシミュレート
        def simulate_disconnection():
            time.sleep(1)
            gui.update_app_status("Chrome", "停止")
            gui.add_log("Chromeを終了しました")

            time.sleep(1)
            gui.update_status(ConnectionStatus.WAITING.value)
            gui.add_log("接続を切断しました")

        thread = threading.Thread(target=simulate_disconnection, daemon=True)
        thread.start()

    gui.set_connect_callback(on_connect)
    gui.set_disconnect_callback(on_disconnect)

    # GUIを実行
    gui.run()
