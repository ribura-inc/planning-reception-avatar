"""
フロントPC用FletベースGUI
接続状態の表示と基本設定を提供
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime

import flet as ft

from ..models.enums import ConnectionStatus
from ..models.schemas import GUIState

logger = logging.getLogger(__name__)


class FrontGUI:
    """フロントPC用のFletベースGUI"""

    def __init__(self):
        # 状態管理
        self.state = GUIState(status=ConnectionStatus.WAITING)
        self._running = False
        self._status_callback: Callable[[str], None] | None = None

        # Fletコンポーネント
        self.page: ft.Page | None = None
        self.status_text: ft.Text | None = None
        self.device_text: ft.Text | None = None
        self.log_column: ft.Column | None = None
        self.log_container: ft.Container | None = None

    def setup_page(self, page: ft.Page) -> None:
        """ページの初期設定"""
        self.page = page
        page.title = "VTuber受付システム - フロントPC"
        page.window.width = 700
        page.window.height = 600
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 20

        # ヘッダー
        header = ft.Container(
            content=ft.Text(
                "VTuber受付システム - フロントPC",
                size=24,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.PRIMARY,
            ),
            margin=ft.margin.only(bottom=20),
        )

        # 接続状態カード
        self.status_text = ft.Text(
            self.state.status.value,
            size=16,
            weight=ft.FontWeight.W_500,
            color=self._get_status_color(self.state.status),
        )

        self.device_text = ft.Text(
            self.state.connected_device or "なし",
            size=14,
        )

        status_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("接続状態", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([
                        ft.Text("状態:", size=14),
                        self.status_text,
                    ]),
                    ft.Row([
                        ft.Text("接続先:", size=14),
                        self.device_text,
                    ]),
                ]),
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
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=8,
            padding=10,
            height=300,
            expand=True,
        )

        log_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("ログ", size=18, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.icons.CLEAR_ALL,
                            tooltip="ログをクリア",
                            on_click=self._clear_log,
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=1),
                    self.log_container,
                ], expand=True),
                padding=20,
            ),
            elevation=2,
            expand=True,
        )

        # ボタンエリア
        button_row = ft.Row([
            ft.FilledButton(
                text="終了",
                icon=ft.icons.CLOSE,
                on_click=self._on_exit,
            ),
        ], alignment=ft.MainAxisAlignment.END)

        # レイアウト構築
        page.add(
            ft.Column([
                header,
                status_card,
                log_card,
                button_row,
            ], expand=True)
        )

        # 初期ログ
        self.add_log("システムを起動しました")
        self.add_log("リモートPCからの接続を待機中...")

    def _get_status_color(self, status: ConnectionStatus) -> str:
        """ステータスに応じた色を取得"""
        color_map = {
            ConnectionStatus.WAITING: ft.colors.ORANGE,
            ConnectionStatus.CONNECTING: ft.colors.BLUE,
            ConnectionStatus.CONNECTED: ft.colors.GREEN,
            ConnectionStatus.ERROR: ft.colors.RED,
            ConnectionStatus.DISCONNECTING: ft.colors.ORANGE,
        }
        return color_map.get(status, ft.colors.PRIMARY)

    def update_status(self, status: str, device: str | None = None) -> None:
        """ステータスの更新"""
        try:
            # Enumに変換
            if status in [s.value for s in ConnectionStatus]:
                status_enum = ConnectionStatus(status)
            else:
                logger.warning(f"Unknown status: {status}")
                return

            self.state.status = status_enum
            if device:
                self.state.connected_device = device

            if self.page and self.status_text:
                self.status_text.value = status_enum.value
                self.status_text.color = self._get_status_color(status_enum)

                if device and self.device_text:
                    self.device_text.value = device
                elif status_enum == ConnectionStatus.WAITING and self.device_text:
                    self.device_text.value = "なし"
                    self.state.connected_device = None

                self.page.update()
        except Exception as e:
            logger.error(f"ステータス更新エラー: {e}")

    def add_log(self, message: str) -> None:
        """ログメッセージの追加"""
        if self.page and self.log_column:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = ft.Container(
                content=ft.Row([
                    ft.Text(f"[{timestamp}]", size=12, color=ft.colors.SECONDARY),
                    ft.Text(message, size=12, expand=True),
                ], spacing=10),
                padding=ft.padding.symmetric(horizontal=5, vertical=2),
            )

            self.log_column.controls.append(log_entry)

            # 最大ログ数を制限
            if len(self.log_column.controls) > 100:
                self.log_column.controls.pop(0)

            self.page.update()

            # 最下部にスクロール
            if self.log_container:
                self.log_container.scroll_to(
                    offset=-1,
                    duration=100,
                )

    def _clear_log(self, e) -> None:
        """ログをクリア"""
        if self.log_column:
            self.log_column.controls.clear()
            self.add_log("ログをクリアしました")

    def _on_exit(self, e) -> None:
        """終了ボタンのハンドラ"""
        self.stop()

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """ステータス変更時のコールバックを設定"""
        self._status_callback = callback

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


def run_gui(status_callback: Callable[[str], None] | None = None) -> FrontGUI:
    """GUI をバックグラウンドスレッドで実行"""
    gui = FrontGUI()
    if status_callback:
        gui.set_status_callback(status_callback)

    thread = threading.Thread(target=gui.run, daemon=True)
    thread.start()

    # GUIの初期化を待つ
    time.sleep(0.5)

    return gui


if __name__ == "__main__":
    # テスト実行
    gui = FrontGUI()

    # テスト用のステータス更新
    def test_updates():
        time.sleep(2)
        gui.update_status(ConnectionStatus.CONNECTING.value, "remote-pc-1")
        gui.add_log("リモートPCから接続要求を受信しました")

        time.sleep(3)
        gui.update_status(ConnectionStatus.CONNECTED.value, "remote-pc-1")
        gui.add_log("接続が確立されました")
        gui.add_log("VTube Studioが起動されました")
        gui.add_log("Meet URLを受信しました")

        time.sleep(5)
        gui.update_status(ConnectionStatus.DISCONNECTING.value)
        gui.add_log("接続を切断しています...")

        time.sleep(2)
        gui.update_status(ConnectionStatus.WAITING.value)
        gui.add_log("接続が切断されました")

    # テストスレッドを開始
    test_thread = threading.Thread(target=test_updates, daemon=True)
    test_thread.start()

    # GUIを実行
    gui.run()
