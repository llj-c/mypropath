"""登录页面对象示例"""

from typing import Optional
from playwright.sync_api import Page

from framework.ui.common.base_page import BasePage


class LoginPage(BasePage):
    """登录页面对象"""

    # 页面元素选择器
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "#login-button"
    ERROR_MESSAGE = "#login-result"

    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        初始化登录页面

        Args:
            page: Playwright Page 实例
            base_url: 基础 URL
        """
        super().__init__(page, base_url)

    def navigate_to_login(self) -> None:
        """导航到登录页面"""
        if self.base_url:
            self.navigate("http://localhost:5173/")
        else:
            # 如果没有 base_url，需要提供完整 URL
            raise ValueError("需要设置 base_url 或提供完整 URL")

    def enter_username(self, username: str) -> None:
        """
        输入用户名

        Args:
            username: 用户名
        """
        self.fill(self.USERNAME_INPUT, username)

    def enter_password(self, password: str) -> None:
        """
        输入密码

        Args:
            password: 密码
        """
        self.fill(self.PASSWORD_INPUT, password)

    def click_login(self) -> None:
        """点击登录按钮"""
        self.click(self.LOGIN_BUTTON)

    def login(self, username: str, password: str) -> None:
        """
        执行登录操作

        Args:
            username: 用户名
            password: 密码
        """
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()


    def get_error_message(self) -> str:
        """
        获取错误消息

        Returns:
            错误消息文本
        """
        return self.get_text(self.ERROR_MESSAGE)

    def is_error_visible(self) -> bool:
        """
        检查错误消息是否可见

        Returns:
            如果错误消息可见返回 True，否则返回 False
        """
        try:
            self.wait_for_selector(self.ERROR_MESSAGE, state="visible", timeout=5000)
            return True
        except Exception:
            return False




