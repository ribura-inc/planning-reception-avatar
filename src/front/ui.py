"""非ITスタッフでも扱いやすい最小構成のフロント用Flet UI。"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import flet as ft

from src.config import Config
from src.models.state import AppStatus, StatusMessage

if TYPE_CHECKING:
    from collections.abc import Callable


class FrontUI:
    """フロントデスク向けのシンプルなステータスボード。"""

    def __init__(self) -> None:
        self.page: ft.Page | None = None
        self._refresh_handler: Callable[[], None] | None = None
        self._ready_handler: Callable[[], None] | None = None

        self.status_label: ft.Text | None = None
        self.detail_label: ft.Text | None = None
        self.network_label: ft.Text | None = None
        self.error_label: ft.Text | None = None

    def bind_handlers(
        self,
        on_refresh: Callable[[], None],
        on_ready: Callable[[], None],
    ) -> None:
        """コントローラーからのコールバックハンドラーを登録する。

        Args:
            on_refresh: ネットワーク再確認時のハンドラー
            on_ready: UI準備完了時のハンドラー
        """
        self._refresh_handler = on_refresh
        self._ready_handler = on_ready

    # ------------------------------------------------------------------
    # コントローラーから呼び出される更新系メソッド
    # ------------------------------------------------------------------
    def update_status(self, payload: StatusMessage) -> None:
        """ステータス更新時の表示変更を行う。

        Args:
            payload: ステータスメッセージ（見出し、詳細、ステータス）
        """
        if not self.page or not self.status_label:
            return
        self.status_label.value = payload.headline if payload.headline else payload.status.value
        if self.detail_label:
            self.detail_label.value = payload.detail or ""
        if payload.status == AppStatus.ERROR:
            self.status_label.color = ft.Colors.RED
        elif payload.status == AppStatus.CONNECTED:
            self.status_label.color = ft.Colors.GREEN
        else:
            self.status_label.color = ft.Colors.BLACK
        self.page.update()

    def show_network_message(self, message: str) -> None:
        """ネットワーク状態メッセージを表示する。

        Args:
            message: 表示するメッセージ
        """
        if not self.page or not self.network_label:
            return
        self.network_label.value = message
        self.page.update()

    def show_error(self, message: str) -> None:
        """エラーメッセージを表示する。

        Args:
            message: 表示するエラーメッセージ（空文字列の場合は非表示）
        """
        if not self.page or not self.error_label:
            return
        self.error_label.value = message
        self.error_label.visible = bool(message)
        self.page.update()

    # ------------------------------------------------------------------
    # Flet 初期化
    # ------------------------------------------------------------------
    def run(self) -> None:
        ft.app(target=self._main)

    def _main(self, page: ft.Page) -> None:
        self.page = page
        page.title = "VTuber Reception - Front"
        page.window.width = Config.UI.Window.FRONT_WIDTH
        page.window.height = Config.UI.Window.FRONT_HEIGHT
        page.padding = Config.UI.Spacing.PAGE_PADDING
        page.theme_mode = ft.ThemeMode.LIGHT

        header = ft.Text("受付ステータス", size=Config.UI.FontSize.HEADER, weight=ft.FontWeight.BOLD)

        self.status_label = ft.Text("待機中", size=Config.UI.FontSize.STATUS_LARGE, weight=ft.FontWeight.W_600)
        self.detail_label = ft.Text(
            "リモートPCからの接続を待っています",
            size=Config.UI.FontSize.DETAIL,
            color=ft.Colors.GREY,
        )
        self.network_label = ft.Text("ネットワークを確認しています...", size=Config.UI.FontSize.SMALL)
        self.error_label = ft.Text("", size=Config.UI.FontSize.SMALL, color=ft.Colors.RED)
        self.error_label.visible = False

        instructions = ft.Text(
            "オペレーターの指示があるまで、この画面をそのままにしてください。",
            size=Config.UI.FontSize.SMALL,
            color=ft.Colors.BLUE_GREY,
        )

        refresh_btn = ft.FilledButton(
            text="ネットワークを再確認",
            icon=ft.Icons.REFRESH,
            on_click=self._handle_refresh,
        )

        page.add(
            ft.Column(
                [
                    header,
                    ft.Container(
                        content=ft.Column([self.status_label, self.detail_label]),
                        padding=ft.padding.all(Config.UI.Spacing.ROW),
                    ),
                    self.network_label,
                    refresh_btn,
                    self.error_label,
                    instructions,
                ],
                spacing=Config.UI.Spacing.LARGE,
            ),
        )

        page.update()

        if self._ready_handler:
            threading.Thread(target=self._ready_handler, daemon=True).start()

    def _handle_refresh(self, _event: ft.ControlEvent) -> None:
        if self._refresh_handler:
            threading.Thread(target=self._refresh_handler, daemon=True).start()
