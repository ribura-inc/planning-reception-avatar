"""リモート用に最小構成で用意したFlet UI。"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import flet as ft

from src.config import Config
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
        """コントローラーからのコールバックハンドラーを登録する。

        Args:
            on_connect: 接続開始時のハンドラー（引数: デバイス名）
            on_disconnect: 切断時のハンドラー
            on_refresh: 再取得時のハンドラー
            on_ready: UI準備完了時のハンドラー
            on_check_google_login: Googleログイン確認ハンドラー
            on_check_extension: 拡張機能確認ハンドラー
            on_open_google_page: Googleログインページを開くハンドラー
            on_open_extension_page: 拡張機能ページを開くハンドラー
        """
        self._connect_handler = on_connect
        self._disconnect_handler = on_disconnect
        self._refresh_handler = on_refresh
        self._ready_handler = on_ready
        self._check_google_login_handler = on_check_google_login
        self._check_extension_handler = on_check_extension
        self._open_google_page_handler = on_open_google_page
        self._open_extension_page_handler = on_open_extension_page

    # ------------------------------------------------------------------
    # 内部ヘルパーメソッド
    # ------------------------------------------------------------------
    def _set_disabled(self, control: ft.Control | None, disabled: bool) -> None:  # noqa: FBT001
        if control is not None:
            control.disabled = disabled

    def _run_async(self, handler: Callable[..., None] | None, *args: object) -> None:
        if handler is None:
            return
        threading.Thread(target=handler, args=args, daemon=True).start()

    def _update_label(
        self,
        label: ft.Text | None,
        value: str,
        *,
        color: str | None = None,
    ) -> None:
        if not label:
            return
        label.value = value
        if color is not None:
            label.color = color

    def _update_precheck_result(self, label: ft.Text | None, result: tuple[bool, str]) -> None:
        if not self.page or not label:
            return
        success, message = result
        self._update_label(
            label,
            message,
            color=ft.Colors.GREEN if success else ft.Colors.RED,
        )
        self.page.update()

    def _update_button_states(self, status: AppStatus) -> None:
        """ステータスに応じてボタンの有効/無効状態を更新する。

        Args:
            status: 現在のアプリケーションステータス
        """
        if status in {AppStatus.CONNECTING, AppStatus.DISCONNECTING, AppStatus.CONNECTED}:
            # 接続中・接続準備中・切断中は接続ボタンを無効化、切断ボタンを有効化
            self._set_disabled(self.connect_button, True)
            self._set_disabled(self.disconnect_button, False)
            self._set_disabled(self.device_dropdown, True)
            # プレチェックボタンも無効化
            self._set_disabled(self.check_google_button, True)
            self._set_disabled(self.check_extension_button, True)

        elif status in {AppStatus.IDLE, AppStatus.ERROR}:
            # 待機中・エラー時は接続ボタンを有効化（デバイスがある場合）
            if self.connect_button:
                self.connect_button.disabled = not self._device_options
            self._set_disabled(self.disconnect_button, True)
            self._set_disabled(self.device_dropdown, False)
            # プレチェックボタンを有効化
            self._set_disabled(self.check_google_button, False)
            self._set_disabled(self.check_extension_button, False)

        elif status == AppStatus.SHUTTING_DOWN:
            # 終了中はすべてのボタンを無効化
            self._set_disabled(self.connect_button, True)
            self._set_disabled(self.disconnect_button, True)
            self._set_disabled(self.check_google_button, True)
            self._set_disabled(self.check_extension_button, True)

    # ------------------------------------------------------------------
    # コントローラーから呼び出される公開API
    # ------------------------------------------------------------------
    def update_status(self, payload: StatusMessage) -> None:
        """ステータス更新時の表示変更を行う。

        Args:
            payload: ステータスメッセージ（見出し、詳細、ステータス）
        """
        if not self.status_label or not self.page:
            return

        # ステータステキストの更新
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
        self._update_button_states(payload.status)

        self.page.update()

    def show_network_message(self, message: str) -> None:
        """ネットワーク状態メッセージを表示する。

        Args:
            message: 表示するメッセージ
        """
        if not self.network_label or not self.page:
            return
        self.network_label.value = message
        self.page.update()

    def update_devices(self, devices: dict[str, str]) -> None:
        """接続先デバイス一覧を更新する。

        Args:
            devices: デバイス名をキー、IPアドレスを値とする辞書
        """
        self._device_options = devices
        if not self.device_dropdown or not self.page:
            return

        options = [ft.dropdown.Option(name) for name in sorted(devices.keys())]
        self.device_dropdown.options = options
        if options:
            if self.device_dropdown.value not in devices:
                self.device_dropdown.value = options[0].key
            self._set_disabled(self.device_dropdown, False)
            self._set_disabled(self.connect_button, False)
        else:
            self.device_dropdown.value = None
            self._set_disabled(self.device_dropdown, True)
            self._set_disabled(self.connect_button, True)
        self.page.update()

    def show_error(self, message: str) -> None:
        """エラーメッセージを表示する。

        Args:
            message: 表示するエラーメッセージ（空文字列の場合は非表示）
        """
        if not self.error_label or not self.page:
            return
        self.error_label.value = message
        self.error_label.visible = bool(message)
        self.page.update()

    def set_session_active(self, active: bool) -> None:  # noqa: FBT001
        """セッションの有効/無効状態を設定する。

        Args:
            active: セッションがアクティブかどうか
        """
        if not self.page:
            return
        self._set_disabled(self.connect_button, active)
        self._set_disabled(self.disconnect_button, not active)
        self._set_disabled(self.device_dropdown, active)
        self.page.update()

    # ------------------------------------------------------------------
    # Flet 初期化
    # ------------------------------------------------------------------
    def run(self) -> None:
        ft.app(target=self._main)

    def _main(self, page: ft.Page) -> None:
        self.page = page
        page.title = "VTuber Reception - Remote"
        page.window.width = Config.UI.Window.REMOTE_WIDTH
        page.window.height = Config.UI.Window.REMOTE_HEIGHT
        page.padding = Config.UI.Spacing.PAGE_PADDING
        page.theme_mode = ft.ThemeMode.LIGHT

        header = ft.Text("リモート接続コントローラ", size=Config.UI.FontSize.TITLE, weight=ft.FontWeight.BOLD)

        self.status_label = ft.Text("状態: 待機中", size=Config.UI.FontSize.STATUS, weight=ft.FontWeight.W_600)
        self.detail_label = ft.Text("", size=Config.UI.FontSize.DETAIL, color=ft.Colors.GREY)
        self.network_label = ft.Text("ネットワーク状態を確認しています...", size=Config.UI.FontSize.SMALL)
        self.error_label = ft.Text("", size=Config.UI.FontSize.SMALL, color=ft.Colors.RED)
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
            size=Config.UI.FontSize.SECTION_HEADER,
            weight=ft.FontWeight.BOLD,
        )

        self.google_login_result_label = ft.Text("未確認", size=Config.UI.FontSize.SMALL)
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

        self.extension_result_label = ft.Text("未確認", size=Config.UI.FontSize.SMALL)
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
                        padding=ft.padding.all(Config.UI.Spacing.CONTAINER),
                    ),
                    ft.Row([self.device_dropdown, refresh_button], alignment=ft.MainAxisAlignment.START),
                    ft.Row([self.connect_button, self.disconnect_button], spacing=Config.UI.Spacing.LARGE),
                    self.error_label,
                    ft.Text(
                        "接続中はChromeブラウザが自動で起動します",
                        size=Config.UI.FontSize.SMALL,
                        color=ft.Colors.GREY,
                    ),
                    ft.Divider(height=20),
                    precheck_header,
                    ft.Row(
                        [self.check_google_button, self.open_google_button],
                        spacing=Config.UI.Spacing.ROW,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    self.google_login_result_label,
                    ft.Row(
                        [self.check_extension_button, self.open_extension_button],
                        spacing=Config.UI.Spacing.ROW,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    self.extension_result_label,
                ],
                spacing=Config.UI.Spacing.SECTION,
            ),
        )

        page.update()

        if self._ready_handler:
            self._run_async(self._ready_handler)

    # ------------------------------------------------------------------
    # UIイベントハンドラー
    # ------------------------------------------------------------------
    def _handle_connect(self, _event: ft.ControlEvent) -> None:
        if not self.device_dropdown:
            return
        device = self.device_dropdown.value
        if not device:
            self.show_error("接続先を選択してください")
            return
        self.set_session_active(True)
        self._run_async(self._connect_handler, device)

    def _handle_disconnect(self, _event: ft.ControlEvent) -> None:
        self.set_session_active(False)
        self._run_async(self._disconnect_handler)

    def _handle_refresh(self, _event: ft.ControlEvent) -> None:
        self._run_async(self._refresh_handler)

    def _handle_check_google_login(self, _event: ft.ControlEvent) -> None:
        """Googleログイン確認ボタン押下時の処理"""
        self._handle_precheck(self._check_google_login_handler, self.google_login_result_label)

    def _handle_check_extension(self, _event: ft.ControlEvent) -> None:
        """拡張機能確認ボタン押下時の処理"""
        self._handle_precheck(self._check_extension_handler, self.extension_result_label)

    def _handle_open_google_page(self, _event: ft.ControlEvent) -> None:
        """Googleログインページを開くボタン押下時の処理"""
        self._run_async(self._open_google_page_handler)

    def _handle_open_extension_page(self, _event: ft.ControlEvent) -> None:
        """拡張機能ページを開くボタン押下時の処理"""
        self._run_async(self._open_extension_page_handler)

    def _handle_precheck(
        self,
        handler: Callable[[], tuple[bool, str]] | None,
        label: ft.Text | None,
    ) -> None:
        if not handler or not label or not self.page:
            return

        def _execute_check() -> None:
            if not self.page:
                return
            self._update_label(label, "確認中...", color=ft.Colors.BLUE)
            self.page.update()
            self._update_precheck_result(label, handler())

        self._run_async(_execute_check)
