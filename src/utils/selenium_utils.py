"""Selenium操作のユーティリティ関数"""

import logging
import time
from collections.abc import Callable

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from src.config import Config

logger = logging.getLogger(__name__)


def wait_for_element_safely(
    driver: WebDriver,
    by: str,
    value: str,
    timeout: int = Config.GoogleMeet.BUTTON_WAIT_TIMEOUT,
) -> WebElement | None:
    """要素が存在・可視・クリック可能になるまで安全に待機

    3段階の確認を行う：
    1. 要素の存在確認
    2. 要素の可視化確認
    3. 要素のクリック可能確認

    Args:
        driver: WebDriverインスタンス
        by: 検索方法（例: By.XPATH）
        value: 検索値（例: XPath文字列）
        timeout: タイムアウト時間（秒）

    Returns:
        WebElement: 見つかった要素、見つからなければNone
    """
    try:
        # Step 1: Check element presence
        element = WebDriverWait(driver, timeout).until(
            expected_conditions.presence_of_element_located((by, value)),
        )
        logger.debug(f"要素が存在します: {value}")

        # Step 2: Check element visibility
        element = WebDriverWait(driver, timeout).until(
            expected_conditions.visibility_of_element_located((by, value)),
        )
        logger.debug(f"要素が可視化されています: {value}")

        # Step 3: Check element clickability
        element = WebDriverWait(driver, timeout).until(
            expected_conditions.element_to_be_clickable((by, value)),
        )
        logger.debug(f"要素がクリック可能です: {value}")

        return element  # noqa: TRY300

    except TimeoutException:
        logger.warning(f"要素が見つかりませんでした（タイムアウト）: {value}")
        return None
    except (NoSuchElementException, StaleElementReferenceException):
        logger.warning(f"要素が見つかりませんでした: {value}")
        return None
    except Exception:
        logger.exception(f"要素の待機中にエラーが発生しました: {value}")
        return None


def retry_operation(
    operation: Callable[[], bool],
    operation_name: str,
    max_attempts: int = Config.GoogleMeet.RETRY_MAX_ATTEMPTS,
    wait_seconds: float = Config.GoogleMeet.RETRY_WAIT_SECONDS,
) -> bool:
    """リトライロジック付きで操作を実行

    Args:
        operation: 実行する操作（成功時True、失敗時Falseを返す関数）
        operation_name: 操作名（ログ出力用）
        max_attempts: 最大リトライ回数
        wait_seconds: リトライ間隔（秒）

    Returns:
        bool: 操作が成功したかどうか
    """
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"{operation_name}を試行中... (試行 {attempt}/{max_attempts})")
            if operation():
                logger.info(f"{operation_name}が成功しました (試行 {attempt}/{max_attempts})")
                return True
            logger.warning(f"{operation_name}が失敗しました (試行 {attempt}/{max_attempts})")
        except Exception:
            logger.exception(f"{operation_name}中にエラーが発生しました (試行 {attempt}/{max_attempts})")

        # 最後の試行でなければ待機
        if attempt < max_attempts:
            logger.info(f"{wait_seconds}秒後にリトライします...")
            time.sleep(wait_seconds)

    logger.error(f"{operation_name}が{max_attempts}回の試行後も失敗しました")
    return False
