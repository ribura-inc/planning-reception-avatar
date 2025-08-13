"""
VTube Studio関連ユーティリティ
VTube Studioの実行状態確認
"""

import logging
import subprocess
import threading
import time
from pathlib import Path

from ..models.enums import Platform
from .platform_utils import PlatformUtils
from .slack import SessionLocation, notify_error

logger = logging.getLogger(__name__)


def _check_vtube_studio_running() -> bool:
    """VTube Studioプロセスが実行中かを確認"""
    return PlatformUtils.check_process_running("VTube Studio")


def _launch_vtube_studio() -> bool:
    """VTube Studioを起動"""
    try:
        current_platform = PlatformUtils.get_platform()
        if current_platform == Platform.WINDOWS:
            vtube_path = "start_without_steam.bat"
            run_bat_in_thread(
                Path("C:/Program Files (x86)/Steam/steamapps/common/VTube Studio"),
                vtube_path,
                detached=True,
            )
        elif current_platform == Platform.MACOS:
            vtube_path = "/Applications/VTube Studio.app"
            subprocess.Popen(["open", vtube_path])
        else:
            logger.error(
                f"Unsupported platform for launching applications: {current_platform}"
            )
            return False

        logger.info(f"Successfully launched: {vtube_path}")

        # 起動まで少し待機
        time.sleep(3)
        return _check_vtube_studio_running()

    except Exception as e:
        logger.error(f"Failed to launch VTube Studio: {e}")
        notify_error(e, "VTube Studio起動", {}, location=SessionLocation.REMOTE)
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


# Windows専用のフラグ（.bat起動用）
CREATE_NEW_CONSOLE: int = 0x00000010
DETACHED_PROCESS: int = 0x00000008
CREATE_NO_WINDOW: int = 0x08000000


def run_bat_in_thread(
    dir_path: str | Path,
    bat_name: str,
    args: list[str] | None = None,
    detached: bool = False,
) -> threading.Thread:
    """指定ディレクトリで .bat を"別スレッド"から非同期起動する.

    指定ディレクトリをカレントディレクトリに設定して .bat を起動する。
    起動はバックグラウンドスレッドで行うため、呼び出しスレッドをブロックしない。

    Args:
        dir_path: .bat を実行したい作業ディレクトリ
        bat_name: 実行する .bat ファイル名（例: "start_server.bat"）
        args: .bat に渡す引数の配列。不要なら None
        detached: True の場合は親プロセスから完全に切り離して（ウィンドウ非表示）起動

    Returns:
        起動担当のスレッドオブジェクト（必要なら .join() 可能）

    Raises:
        RuntimeError: Windows 以外のOSで呼び出された場合
        FileNotFoundError: .bat ファイルが存在しない場合
        ValueError: bat_name が .bat でない場合
    """
    cwd: Path = Path(dir_path).resolve()
    bat_path: Path = (cwd / bat_name).resolve()

    if not bat_path.exists():
        raise FileNotFoundError(str(bat_path))
    if bat_path.suffix.lower() != ".bat":
        raise ValueError("bat_name には拡張子 .bat を指定すること")

    argv: list[str] = ["cmd.exe", "/c", "call", str(bat_path), *(args or [])]
    creationflags: int = (
        DETACHED_PROCESS | CREATE_NO_WINDOW if detached else CREATE_NEW_CONSOLE
    )

    def _target() -> None:
        # ここで起動を実施（非同期・別スレッド）
        subprocess.Popen(
            argv,
            cwd=str(cwd),
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            shell=False,
        )

    th = threading.Thread(
        target=_target, name=f"bat-launch:{bat_path.name}", daemon=True
    )
    th.start()
    return th
