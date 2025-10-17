"""シンプル化したフロントアプリのエントリーポイント。"""

from __future__ import annotations

from src.utils.error_handler import handle_uncaught_exception
from src.utils.notification_service import FrontNotifier
from src.utils.slack import SessionLocation

from .controller import FrontController
from .ui import FrontUI


def main() -> None:
    """フロントPCアプリケーションのエントリーポイント"""
    # 想定外エラーをSlack通知する最終防衛ラインを設置
    handle_uncaught_exception(SessionLocation.FRONT, "フロントPC")

    notifier = FrontNotifier(location=SessionLocation.FRONT)
    notifier.app_started()

    controller = FrontController(notifier=notifier)
    ui = FrontUI()

    controller.attach_callbacks(
        status_callback=ui.update_status,
        network_callback=ui.show_network_message,
        error_callback=ui.show_error,
    )

    ui.bind_handlers(
        on_refresh=controller.retry_network,
        on_ready=controller.initialize,
    )

    try:
        ui.run()
    finally:
        controller.shutdown()
        notifier.app_stopped()


if __name__ == "__main__":
    main()
