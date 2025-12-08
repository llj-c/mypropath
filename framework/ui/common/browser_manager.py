"""浏览器管理器，封装 Playwright 浏览器和上下文管理"""

from typing import Optional, Literal
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from framework.ui.common.ui_exceptions import UIError


class BrowserManager:
    """浏览器管理器，负责管理 Playwright 浏览器实例和上下文"""

    def __init__(
        self,
        browser_type: Literal["chromium", "firefox", "webkit"] = "chromium",
        headless: bool = False,
        viewport_size: Optional[dict] = None,
        base_url: Optional[str] = None,
    ):
        """
        初始化浏览器管理器

        Args:
            browser_type: 浏览器类型，可选值：chromium, firefox, webkit
            headless: 是否无头模式
            viewport_size: 视口大小，格式：{"width": 1920, "height": 1080}
            base_url: 基础 URL，用于相对路径导航
        """
        self.browser_type = browser_type
        self.headless = headless
        self.viewport_size = viewport_size or {"width": 1920, "height": 1080}
        self.base_url = base_url

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> BrowserContext:
        """
        启动浏览器并创建上下文

        Returns:
            BrowserContext 实例
        """
        if self._context is not None:
            return self._context

        try:
            self._playwright = sync_playwright().start()

            # 根据浏览器类型启动对应的浏览器
            if self.browser_type == "chromium":
                self._browser = self._playwright.chromium.launch(headless=self.headless,slow_mo=2000)
            elif self.browser_type == "firefox":
                self._browser = self._playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == "webkit":
                self._browser = self._playwright.webkit.launch(headless=self.headless)
            else:
                raise UIError(f"不支持的浏览器类型: {self.browser_type}")

            # 创建浏览器上下文
            self._context = self._browser.new_context(
                viewport=self.viewport_size,
                base_url=self.base_url,
            )

            return self._context

        except Exception as e:
            raise UIError(f"启动浏览器失败: {e}") from e

    def launch_browser(self, browser_type: Literal["chromium", "firefox", "webkit"] = "chromium", headless: bool = True) -> Browser:
        if self._playwright is None:
            raise UIError("Playwright 未初始化")

        if browser_type == "chromium":
            return self._playwright.chromium.launch(headless=headless)
        elif browser_type == "firefox":
            return self._playwright.firefox.launch(headless=headless)
        elif browser_type == "webkit":
            return self._playwright.webkit.launch(headless=headless)
        else:
            raise UIError(f"不支持的浏览器类型: {browser_type}")

    def new_page(self) -> Page:
        """
        创建新页面

        Returns:
            Page 实例
        """
        if self._context is None:
            self.start()

        if self._context is None:
            raise UIError("浏览器上下文未初始化")

        return self._context.new_page()

    def close(self) -> None:
        """关闭浏览器和上下文"""
        if self._context:
            self._context.close()
            self._context = None

        if self._browser:
            self._browser.close()
            self._browser = None

        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
