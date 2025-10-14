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
    )

    try:
        ui.run()
    finally:
        controller.shutdown()
        notifier.app_stopped()


if __name__ == "__main__":
    main()
