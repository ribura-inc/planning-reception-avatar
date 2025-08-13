"""
プラットフォーム判定と OS 固有処理のユーティリティ
"""

import logging
import platform as platform_module
import subprocess

from ..models.enums import Platform, ProcessName

logger = logging.getLogger(__name__)


class PlatformUtils:
    """OS固有の処理を統一的に扱うためのユーティリティクラス"""

    @staticmethod
    def get_platform() -> Platform:
        """現在のプラットフォームを取得"""
        system = platform_module.system()
        return Platform.from_system(system)

    @staticmethod
    def check_process_running(process_name: str) -> bool:
        """プロセスが実行中かどうかを確認"""
        current_platform = PlatformUtils.get_platform()

        try:
            if current_platform == Platform.WINDOWS:
                # Windowsではtasklistを使用
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {process_name}*"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return process_name.lower() in result.stdout.lower()
            else:
                # macOS/Linuxではpgrepを使用
                result = subprocess.run(
                    ["pgrep", "-f", process_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while checking process: {process_name}")
            return False
        except Exception as e:
            logger.error(f"Error checking process {process_name}: {e}")
            return False

    @staticmethod
    def get_chrome_process_name() -> str:
        """プラットフォーム別のChromeプロセス名を取得"""
        current_platform = PlatformUtils.get_platform()
        process_name = ProcessName.get_chrome_process(current_platform)
        return process_name.value
