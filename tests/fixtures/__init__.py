"""测试 fixtures 模块"""

# 导入所有 fixtures，使 pytest 能够发现它们
from tests.fixtures.ui_fixtures import (  # noqa: F401
    browser_manager,
    page,
    login_page,
)

