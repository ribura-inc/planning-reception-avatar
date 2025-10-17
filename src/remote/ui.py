"""リモート用に最小構成で用意したFlet UI。"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import flet as ft

from src.models.state import AppStatus, StatusMessage

if TYPE_CHECKING:
    from collections.abc import Callable


class RemoteUI:
    """リモート作業者向けの簡潔なUI。"""

    def __init__(self) -> None:
        self.page: ft.Page | None = None
        self._connect_handler: Callable[[str], None] | None = None
        self._disconnect_handler: Callable[[], None] | None = None
        self._refresh_handler: Callable[[], None] | None = None
        self._ready_handler: Callable[[], None] | None = None
        self._check_google_login_handler: Callable[[], tuple[bool, str]] | None = None
        self._check_extension_handler: Callable[[], tuple[bool, str]] | None = None
        self._open_google_page_handler: Callable[[], None] | None = None
        self._open_extension_page_handler: Callable[[], None] | None = None

        self._device_options: dict[str, str] = {}

        # `build`内で初期化する各UI要素
        self.status_label: ft.Text | None = None
        self.detail_label: ft.Text | None = None
        self.network_label: ft.Text | None = None
        self.error_label: ft.Text | None = None
        self.device_dropdown: ft.Dropdown | None = None
        self.connect_button: ft.FilledButton | None = None
        self.disconnect_button: ft.OutlinedButton | None = None
        self.google_login_result_label: ft.Text | None = None
        self.extension_result_label: ft.Text | None = None
        self.check_google_button: ft.ElevatedButton | None = None
        self.check_extension_button: ft.ElevatedButton | None = None
        self.open_google_button: ft.TextButton | None = None
        self.open_extension_button: ft.TextButton | None = None

    # ------------------------------------------------------------------
    # ハンドラー登録
    # ------------------------------------------------------------------
    def bind_handlers(
        self,
        on_connect: Callable[[str], None],
        on_disconnect: Callable[[], None],
        on_refresh: Callable[[], None],
        on_ready: Callable[[], None],
        on_check_google_login: Callable[[], tuple[bool, str]] | None = None,
        on_check_extension: Callable[[], tuple[bool, str]] | None = None,
        on_open_google_page: Callable[[], None] | None = None,
        on_open_extension_page: Callable[[], None] | None = None,
    ) -> None:
        self._connect_handler = on_connect
        self._disconnect_handler = on_disconnect
        self._refresh_handler = on_refresh
        self._ready_handler = on_ready
        self._check_google_login_handler = on_check_google_login
        self._check_extension_handler = on_check_extension
        self._open_google_page_handler = on_open_google_page
        self._open_extension_page_handler = on_open_extension_page

    # ------------------------------------------------------------------
    # コントローラーから呼び出される公開API
    # ------------------------------------------------------------------
    def update_status(self, payload: StatusMessage) -> None:  # noqa: C901, PLR0912, PLR0915
        if not self.status_label or not self.page:
            return
        self.status_label.value = payload.headline if payload.headline else payload.status.value
        if self.detail_label:
            self.detail_label.value = payload.detail or ""

        # ステータスに応じた色付け
        if payload.status == AppStatus.ERROR:
            self.status_label.color = ft.Colors.RED
        elif payload.status == AppStatus.CONNECTED:
            self.status_label.color = ft.Colors.GREEN
        else:
            self.status_label.color = ft.Colors.BLACK

        # ボタンの有効/無効制御
        if payload.status in {AppStatus.CONNECTING, AppStatus.DISCONNECTING}:
            if self.connect_button:
                self.connect_button.disabled = True
            if self.disconnect_button:
                self.disconnect_button.disabled = False
            if self.device_dropdown:
                self.device_dropdown.disabled = True
            # 接続中は確認ボタンを無効化
            if self.check_google_button:
                self.check_google_button.disabled = True
            if self.check_extension_button:
                self.check_extension_button.disabled = True
        elif payload.status == AppStatus.CONNECTED:
            if self.connect_button:
                self.connect_button.disabled = True
            if self.disconnect_button:
                self.disconnect_button.disabled = False
            # 接続中は確認ボタンを無効化
            if self.check_google_button:
                self.check_google_button.disabled = True
            if self.check_extension_button:
                self.check_extension_button.disabled = True
        elif payload.status in {AppStatus.IDLE, AppStatus.ERROR}:
            if self.connect_button:
                self.connect_button.disabled = not self._device_options
            if self.disconnect_button:
                self.disconnect_button.disabled = True
            if self.device_dropdown:
                self.device_dropdown.disabled = False
            # 待機中/エラー時は確認ボタンを有効化
            if self.check_google_button:
                self.check_google_button.disabled = False
            if self.check_extension_button:
                self.check_extension_button.disabled = False
        elif payload.status == AppStatus.SHUTTING_DOWN:
            if self.connect_button:
                self.connect_button.disabled = True
            if self.disconnect_button:
                self.disconnect_button.disabled = True
            # 終了中は確認ボタンを無効化
            if self.check_google_button:
                self.check_google_button.disabled = True
            if self.check_extension_button:
                self.check_extension_button.disabled = True

        self.page.update()

    def show_network_message(self, message: str) -> None:
        if not self.network_label or not self.page:
            return
        self.network_label.value = message
        self.page.update()

    def update_devices(self, devices: dict[str, str]) -> None:
        self._device_options = devices
        if not self.device_dropdown or not self.page:
            return

        options = [ft.dropdown.Option(name) for name in sorted(devices.keys())]
        self.device_dropdown.options = options
        if options:
            if self.device_dropdown.value not in devices:
                self.device_dropdown.value = options[0].key
            self.device_dropdown.disabled = False
            if self.connect_button:
                self.connect_button.disabled = False
        else:
            self.device_dropdown.value = None
            self.device_dropdown.disabled = True
            if self.connect_button:
                self.connect_button.disabled = True
        self.page.update()

    def show_error(self, message: str) -> None:
        if not self.error_label or not self.page:
            return
        self.error_label.value = message
        self.error_label.visible = bool(message)
        self.page.update()

    def set_session_active(self, active: bool) -> None:  # noqa: FBT001
        if not self.page:
            return
        if self.connect_button:
            self.connect_button.disabled = active
        if self.disconnect_button:
            self.disconnect_button.disabled = not active
        if self.device_dropdown:
            self.device_dropdown.disabled = active
        self.page.update()

    # ------------------------------------------------------------------
    # Flet 初期化
    # ------------------------------------------------------------------
    def run(self) -> None:
        ft.app(target=self._main)

    def _main(self, page: ft.Page) -> None:
        self.page = page
        page.title = "VTuber Reception - Remote"
        page.window.width = 1000
        page.window.height = 800
        page.padding = 24
        page.theme_mode = ft.ThemeMode.LIGHT

        header = ft.Text("リモート接続コントローラ", size=24, weight=ft.FontWeight.BOLD)

        self.status_label = ft.Text("状態: 待機中", size=20, weight=ft.FontWeight.W_600)
        self.detail_label = ft.Text("", size=14, color=ft.Colors.GREY)
        self.network_label = ft.Text("ネットワーク状態を確認しています...", size=12)
        self.error_label = ft.Text("", size=12, color=ft.Colors.RED)
        self.error_label.visible = False

        self.device_dropdown = ft.Dropdown(
            label="接続先",
            options=[],
            width=320,
            disabled=True,
        )

        refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="接続先を再取得",
            on_click=self._handle_refresh,
        )

        self.connect_button = ft.FilledButton(
            text="接続を開始",
            icon=ft.Icons.PLAY_ARROW,
            disabled=True,
            on_click=self._handle_connect,
        )

        self.disconnect_button = ft.OutlinedButton(
            text="セッション終了",
            icon=ft.Icons.STOP_CIRCLE,
            disabled=True,
            on_click=self._handle_disconnect,
        )

        # Precheckセクション
        precheck_header = ft.Text(
            "事前チェック（一定期間空いてから作動させる場合は、事前チェックで問題ないことをご確認ください）",
            size=18,
            weight=ft.FontWeight.BOLD,
        )

        self.google_login_result_label = ft.Text("未確認", size=12)
        self.check_google_button = ft.ElevatedButton(
            text="Googleログイン確認",
            icon=ft.Icons.LOGIN,
            on_click=self._handle_check_google_login,
        )
        self.open_google_button = ft.TextButton(
            text="Googleログインページを開く",
            icon=ft.Icons.OPEN_IN_BROWSER,
            on_click=self._handle_open_google_page,
        )

        self.extension_result_label = ft.Text("未確認", size=12)
        self.check_extension_button = ft.ElevatedButton(
            text="拡張機能確認",
            icon=ft.Icons.EXTENSION,
            on_click=self._handle_check_extension,
        )
        self.open_extension_button = ft.TextButton(
            text="拡張機能ページを開く",
            icon=ft.Icons.OPEN_IN_BROWSER,
            on_click=self._handle_open_extension_page,
        )

        page.add(
            ft.Column(
                [
                    header,
                    ft.Container(
                        content=ft.Column(
                            [self.status_label, self.detail_label, self.network_label],
                        ),
                        padding=ft.padding.all(12),
                    ),
                    ft.Row([self.device_dropdown, refresh_button], alignment=ft.MainAxisAlignment.START),
                    ft.Row([self.connect_button, self.disconnect_button], spacing=16),
                    self.error_label,
                    ft.Text("接続中はChromeブラウザが自動で起動します", size=12, color=ft.Colors.GREY),
                    ft.Divider(height=20),
                    precheck_header,
                    ft.Row(
                        [self.check_google_button, self.open_google_button],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    self.google_login_result_label,
                    ft.Row(
                        [self.check_extension_button, self.open_extension_button],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    self.extension_result_label,
                ],
                spacing=18,
            ),
        )

        page.update()

        if self._ready_handler:
            threading.Thread(target=self._ready_handler, daemon=True).start()

    # ------------------------------------------------------------------
    # UIイベントハンドラー
    # ------------------------------------------------------------------
    def _handle_connect(self, _event: ft.ControlEvent) -> None:
        if not self._connect_handler or not self.device_dropdown:
            return
        device = self.device_dropdown.value
        if not device:
            self.show_error("接続先を選択してください")
            return
        self.set_session_active(True)
        thread = threading.Thread(target=self._connect_handler, args=(device,), daemon=True)
        thread.start()

    def _handle_disconnect(self, _event: ft.ControlEvent) -> None:
        if not self._disconnect_handler:
            return
        self.set_session_active(False)
        thread = threading.Thread(target=self._disconnect_handler, daemon=True)
        thread.start()

    def _handle_refresh(self, _event: ft.ControlEvent) -> None:
        if self._refresh_handler:
            thread = threading.Thread(target=self._refresh_handler, daemon=True)
            thread.start()

    def _handle_check_google_login(self, _event: ft.ControlEvent) -> None:
        """Googleログイン確認ボタン押下時の処理"""
        if not self._check_google_login_handler or not self.google_login_result_label or not self.page:
            return

        def _run_check() -> None:
            if not self._check_google_login_handler or not self.google_login_result_label or not self.page:
                return
            self.google_login_result_label.value = "確認中..."
            self.google_login_result_label.color = ft.Colors.BLUE
            self.page.update()

            success, message = self._check_google_login_handler()

            self.google_login_result_label.value = message
            self.google_login_result_label.color = ft.Colors.GREEN if success else ft.Colors.RED
            self.page.update()

        thread = threading.Thread(target=_run_check, daemon=True)
        thread.start()

    def _handle_check_extension(self, _event: ft.ControlEvent) -> None:
        """拡張機能確認ボタン押下時の処理"""
        if not self._check_extension_handler or not self.extension_result_label or not self.page:
            return

        def _run_check() -> None:
            if not self._check_extension_handler or not self.extension_result_label or not self.page:
                return
            self.extension_result_label.value = "確認中..."
            self.extension_result_label.color = ft.Colors.BLUE
            self.page.update()

            success, message = self._check_extension_handler()

            self.extension_result_label.value = message
            self.extension_result_label.color = ft.Colors.GREEN if success else ft.Colors.RED
            self.page.update()

        thread = threading.Thread(target=_run_check, daemon=True)
        thread.start()

    def _handle_open_google_page(self, _event: ft.ControlEvent) -> None:
        """Googleログインページを開くボタン押下時の処理"""
        if not self._open_google_page_handler:
            return
        thread = threading.Thread(target=self._open_google_page_handler, daemon=True)
        thread.start()

    def _handle_open_extension_page(self, _event: ft.ControlEvent) -> None:
        """拡張機能ページを開くボタン押下時の処理"""
        if not self._open_extension_page_handler:
            return
        thread = threading.Thread(target=self._open_extension_page_handler, daemon=True)
        thread.start()
