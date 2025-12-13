# conftest.py
"""pytest 配置文件，用于测试环境的设置"""

# import sys
# from pathlib import Path

# # 将项目根目录添加到 Python 路径
# project_root = Path(__file__).parent.parent
# if str(project_root) not in sys.path:
#     sys.path.insert(0, str(project_root))

# 导入任务管理插件（确保插件被注册）
# pytest会自动发现并加载插件
import logging

import pytest

from framework.pytest_plugin.task_plugin import TaskPlugin


def pytest_addoption(parser):
    """添加pytest命令行选项"""
    parser.addoption(
        "--run-id",
        action="store",
        default=None,
        help="测试任务的run_id，用于任务管理",
    )


def pytest_configure(config:pytest.Config):
    """pytest配置钩子 - 注册插件"""
    # 创建插件实例并注册
    plugin = TaskPlugin(config)
    plugin._setup_logging()
    print(f"pytest_configure: {plugin}")
    config.pluginmanager.register(plugin, "task_plugin")
        # 禁用pytest内置日志插件，避免冲突（关键！）
    config.option.log_cli = False
    config.option.log_file = None
    config.option.log_level = None


@pytest.fixture(scope="session", autouse=True)
def test_logger():  
    return logging.getLogger("test")
