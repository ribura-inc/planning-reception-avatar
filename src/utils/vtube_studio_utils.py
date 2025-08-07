"""
VTube Studio関連ユーティリティ
VTube Studioの実行状態確認
"""

import logging
import time

from .platform_utils import PlatformUtils

logger = logging.getLogger(__name__)


def _check_vtube_studio_running() -> bool:
    """VTube Studioプロセスが実行中かを確認"""
    return PlatformUtils.check_process_running("VTube Studio")


def _launch_vtube_studio() -> bool:
    """VTube Studioを起動"""
    try:
        # プラットフォーム別のパスを取得
        vtube_paths = PlatformUtils.get_vtube_studio_paths()
        vtube_path = PlatformUtils.find_executable(vtube_paths)

        if not vtube_path:
            logger.error("VTube Studio application not found")
            return False

        logger.info(f"Starting VTube Studio from: {vtube_path}")

        if PlatformUtils.launch_application(vtube_path):
            # 起動まで少し待機
            time.sleep(3)
            return _check_vtube_studio_running()
        else:
            return False

    except Exception as e:
        logger.error(f"Failed to launch VTube Studio: {e}")
        return False


def check_and_setup_vtube_studio() -> tuple[bool, str]:
    """
    VTube Studioの実行状態を確認し、必要に応じて起動

    Returns:
        (success, message): 成功フラグとメッセージ
    """
    if _check_vtube_studio_running():
        return True, "VTube Studio is running"

    logger.info("VTube Studio not running, attempting to launch...")

    if _launch_vtube_studio():
        # 起動後の確認（最大10秒待機）
        for _i in range(10):
            time.sleep(1)
            if _check_vtube_studio_running():
                return True, "VTube Studio launched successfully"

        return False, "VTube Studio launched but process not detected"
    else:
        return False, "Failed to launch VTube Studio"
