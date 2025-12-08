"""基础页面类，封装 Playwright Page 对象的常用操作"""

from typing import Optional, Dict, Any, Literal
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

from framework.ui.common.ui_exceptions import (
    ElementNotFoundError,
    ElementNotVisibleError,
    TimeoutError,
    NavigationError,
)


class BasePage:
    """基础页面类，提供页面操作的通用方法"""

    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        初始化基础页面

        Args:
            page: Playwright Page 实例
            base_url: 基础 URL，用于相对路径导航
        """
        self.page = page
        self.base_url = base_url

    def navigate(self, url: str, wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] | None = "load", timeout: int = 30000) -> None:
        """
        导航到指定 URL

        Args:
            url: 目标 URL（如果是相对路径，需要设置 base_url）
            wait_until: 等待条件，可选值：load, domcontentloaded, networkidle, commit
            timeout: 超时时间（毫秒）

        Raises:
            NavigationError: 导航失败时抛出
        """
        try:
            self.page.goto(url, wait_until=wait_until, timeout=timeout)
        except PlaywrightTimeoutError as e:
            raise NavigationError(f"页面导航超时: {url}") from e
        except Exception as e:
            raise NavigationError(f"页面导航失败: {url}") from e

    def get_locator(self, selector: str) -> Locator:
        """
        获取元素定位器

        Args:
            selector: CSS 选择器或文本选择器

        Returns:
            Locator 实例
        """
        return self.page.locator(selector)

    def click(
        self,
        selector: str,
        timeout: int = 30000,
        force: bool = False,
    ) -> None:
        """
        点击元素

        Args:
            selector: 元素选择器
            timeout: 超时时间（毫秒）
            force: 是否强制点击（即使元素不可见）

        Raises:
            ElementNotFoundError: 元素未找到时抛出
            ElementNotVisibleError: 元素不可见时抛出
        """
        try:
            locator = self.get_locator(selector)
            if force:
                locator.click(timeout=timeout, force=True)
            else:
                locator.click(timeout=timeout)
        except PlaywrightTimeoutError as e:
            if "not visible" in str(e).lower():
                raise ElementNotVisibleError(f"元素不可见: {selector}") from e
            raise ElementNotFoundError(f"元素未找到或超时: {selector}") from e

    def fill(
        self,
        selector: str,
        value: str,
        timeout: int = 30000,
    ) -> None:
        """
        填充输入框

        Args:
            selector: 输入框选择器
            value: 要填充的值
            timeout: 超时时间（毫秒）

        Raises:
            ElementNotFoundError: 元素未找到时抛出
        """
        try:
            self.get_locator(selector).fill(value, timeout=timeout)
        except PlaywrightTimeoutError as e:
            raise ElementNotFoundError(f"输入框未找到或超时: {selector}") from e

    def get_text(self, selector: str, timeout: int = 30000) -> str:
        """
        获取元素文本内容

        Args:
            selector: 元素选择器
            timeout: 超时时间（毫秒）

        Returns:
            元素文本内容

        Raises:
            ElementNotFoundError: 元素未找到时抛出
        """
        try:
            return self.get_locator(selector).inner_text(timeout=timeout)
        except PlaywrightTimeoutError as e:
            raise ElementNotFoundError(f"元素未找到或超时: {selector}") from e

    def wait_for_selector(
        self,
        selector: str,
        state: Literal['attached', 'detached', 'hidden', 'visible'] | None = "visible",
        timeout: int = 30000,
    ) -> Locator:
        """
        等待元素出现

        Args:
            selector: 元素选择器
            state: 等待状态，可选值：attached, detached, visible, hidden
            timeout: 超时时间（毫秒）

        Returns:
            Locator 实例

        Raises:
            TimeoutError: 超时时抛出
        """
        try:
            self.page.wait_for_selector(selector, state=state, timeout=timeout)
            return self.get_locator(selector)
        except PlaywrightTimeoutError as e:
            raise TimeoutError(f"等待元素超时: {selector}") from e

    def wait_for_url(
        self,
        url_pattern: str,
        timeout: int = 30000,
    ) -> None:
        """
        等待 URL 匹配指定模式

        Args:
            url_pattern: URL 模式（支持正则表达式）
            timeout: 超时时间（毫秒）

        Raises:
            TimeoutError: 超时时抛出
        """
        try:
            self.page.wait_for_url(url_pattern, timeout=timeout)
        except PlaywrightTimeoutError as e:
            raise TimeoutError(f"等待 URL 超时: {url_pattern}") from e

    def take_screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
    ) -> bytes:
        """
        截图

        Args:
            path: 保存路径（可选，不提供则返回字节）
            full_page: 是否截取整个页面

        Returns:
            截图字节数据（如果提供了 path，则返回空字节）
        """
        return self.page.screenshot(path=path, full_page=full_page)

    def get_title(self) -> str:
        """
        获取页面标题

        Returns:
            页面标题
        """
        return self.page.title()

    def get_url(self) -> str:
        """
        获取当前页面 URL

        Returns:
            当前页面 URL
        """
        return self.page.url

    def refresh(self, wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] | None = "load", timeout: int = 30000) -> None:
        """
        刷新页面

        Args:
            wait_until: 等待条件
            timeout: 超时时间（毫秒）
        """
        self.page.reload(wait_until=wait_until, timeout=timeout)

    def go_back(self, timeout: int = 30000) -> None:
        """
        返回上一页

        Args:
            timeout: 超时时间（毫秒）
        """
        self.page.go_back(timeout=timeout)

    def go_forward(self, timeout: int = 30000) -> None:
        """
        前进到下一页

        Args:
            timeout: 超时时间（毫秒）
        """
        self.page.go_forward(timeout=timeout)
