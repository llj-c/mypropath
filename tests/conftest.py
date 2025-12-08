"""pytest 配置文件，用于测试环境的设置"""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入任务管理插件（确保插件被注册）
# pytest会自动发现并加载插件
from framework.pytest_plugin import task_plugin  # noqa: F401

# 导入 UI fixtures（pytest 会自动发现）
# 需要显式导入 fixture 函数，这样 pytest 才能发现它们
from tests.fixtures.ui_fixtures import (  # noqa: F401
    browser_manager,
    page,
    login_page,
)

