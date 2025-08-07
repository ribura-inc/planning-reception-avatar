"""
フロントPC用FletベースGUI
接続状態の表示と基本設定を提供
"""

import logging
from collections.abc import Callable
from datetime import datetime

import flet as ft
from flet.core.colors import Colors
from flet.core.icons import Icons

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
                color=Colors.PRIMARY,
            ),
            margin=ft.margin.only(bottom=20),
        )

        # 接続状態カード
        self.status_text = ft.Text(
            self.state.status,
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
                content=ft.Column(
                    [
                        ft.Text("接続状態", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=1),
                        ft.Row(
                            [
                                ft.Text("状態:", size=14),
                                self.status_text,
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Text("接続先:", size=14),
                                self.device_text,
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
            height=300,
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
                    status_card,
                    log_card,
                    button_row,
                ],
                expand=True,
            )
        )

        # 初期ログ
        self.add_log("システムを起動しました")
        self.add_log("リモートPCからの接続を待機中...")

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

    def update_status(
        self, status_enum: ConnectionStatus, device: str | None = None
    ) -> None:
        """ステータスの更新"""
        try:
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

    def _on_exit(self, e) -> None:
        """終了ボタンのハンドラ"""
        self.stop()

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
