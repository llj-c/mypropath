"""UI 测试 fixtures"""

import pytest
from playwright.sync_api import Page

from framework.ui.common.browser_manager import BrowserManager
from framework.ui.pages.login_page import LoginPage


@pytest.fixture(scope="session")
def browser_manager():
    """
    浏览器管理器 fixture（session 级别，所有测试共享一个浏览器实例）

    Yields:
        BrowserManager 实例
    """
    manager = BrowserManager(
        browser_type="chromium",
        headless=False,
        viewport_size={"width": 1920, "height": 1080},
        base_url="https://example.com",  # 根据实际情况修改
    )

    manager.start()
    yield manager
    manager.close()


@pytest.fixture(scope="function")
def page(browser_manager):
    """
    页面 fixture（function 级别，每个测试函数创建一个新页面）

    Args:
        browser_manager: 浏览器管理器 fixture

    Yields:
        Page 实例
    """
    page = browser_manager.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def login_page(page):
    """
    登录页面对象 fixture

    Args:
        page: Page fixture

    Returns:
        LoginPage 实例
    """
    return LoginPage(page, base_url="https://example.com")  # 根据实际情况修改




