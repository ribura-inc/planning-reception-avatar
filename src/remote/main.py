"""スリム化したリモートアプリのエントリーポイント。"""

from __future__ import annotations

from src.utils.notification_service import RemoteNotifier
from src.utils.slack import SessionLocation

from .controller import RemoteController
from .ui import RemoteUI


def main() -> None:
    notifier = RemoteNotifier(location=SessionLocation.REMOTE)
    notifier.app_started()

    controller = RemoteController(notifier)
    ui = RemoteUI()

    controller.attach_callbacks(
        status_callback=ui.update_status,
        network_callback=ui.show_network_message,
        devices_callback=ui.update_devices,
        error_callback=ui.show_error,
    )

    ui.bind_handlers(
        on_connect=controller.start_session,
        on_disconnect=controller.end_session,
        on_refresh=controller.refresh_devices,
        on_ready=controller.initialize,
        on_check_google_login=controller.check_google_login,
        on_check_extension=controller.check_extension_installed,
        on_open_google_page=controller.open_google_login_page,
        on_open_extension_page=controller.open_extension_page,
    )

    try:
        ui.run()
    finally:
        controller.shutdown()
        notifier.app_stopped()


if __name__ == "__main__":
    main()
