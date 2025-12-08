"""登录页面测试示例（演示如何使用封装的 Playwright）"""

import pytest
from framework.ui.pages.login_page import LoginPage


class TestLoginPage:
    """登录页面测试类"""

    def test_login_success(self, login_page: LoginPage):
        """测试成功登录"""
        # Arrange: 准备测试数据
        username = "admin"
        password = "123456"

        # Act: 执行登录操作
        login_page.navigate_to_login()
        login_page.login(username, password)

        # Assert: 验证登录成功（根据实际情况修改断言）
        # 例如：等待跳转到首页
        error_message = login_page.get_error_message()
        assert "success" in error_message.lower()

    # def test_login_with_invalid_credentials(self, login_page):
    #     """测试使用无效凭据登录"""
    #     # Arrange
    #     username = "invalid_user"
    #     password = "wrong_password"

    #     # Act
    #     login_page.navigate_to_login()
    #     login_page.login(username, password)

    #     # Assert: 验证显示错误消息
    #     assert login_page.is_error_visible()
    #     error_message = login_page.get_error_message()
    #     assert "invalid" in error_message.lower() or "错误" in error_message

    # def test_login_with_empty_username(self, login_page):
    #     """测试使用空用户名登录"""
    #     # Arrange
    #     username = ""
    #     password = "test_password"

    #     # Act
    #     login_page.navigate_to_login()
    #     login_page.enter_password(password)
    #     login_page.click_login()

    #     # Assert: 验证显示验证错误
    #     assert login_page.is_error_visible()

    # def test_navigation_to_login_page(self, login_page):
    #     """测试导航到登录页面"""
    #     # Act
    #     login_page.navigate_to_login()

    #     # Assert: 验证页面标题或 URL
    #     assert "login" in login_page.get_url().lower() or "登录" in login_page.get_title().lower()
