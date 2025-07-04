"""
VTube Studio関連ユーティリティ
VTube Studioの実行状態確認
"""

import logging
import subprocess

logger = logging.getLogger(__name__)


def check_vtube_studio_running() -> bool:
    """VTube Studioプロセスが実行中かを確認"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "VTube Studio"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            logger.info("VTube Studio process is running")
            return True
        else:
            logger.warning("VTube Studio process not found")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Timeout while checking VTube Studio process")
        return False
    except Exception as e:
        logger.error(f"Error checking VTube Studio process: {e}")
        return False


def check_and_setup_vtube_studio() -> tuple[bool, str]:
    """
    VTube Studioの実行状態を確認

    Returns:
        (success, message): 成功フラグとメッセージ
    """
    if check_vtube_studio_running():
        return True, "VTube Studio is running"
    else:
        return False, "VTube Studio is not running"
