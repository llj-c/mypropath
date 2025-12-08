"""pytest任务管理插件 - 实现任务状态检查、暂停/中止控制等功能"""

import logging
from pathlib import Path
from typing import Optional

import pytest

from framework.task.state_store import StateStore, TaskStatus
from framework.task.traceid import (
    generate_traceid,
    set_traceid,
    get_traceid,
    clear_traceid,
)

logger = logging.getLogger(__name__)


class TaskPlugin:
    """pytest任务管理插件"""

    def __init__(self, config):
        """初始化插件"""
        self.config = config
        self.run_id: Optional[str] = None
        self.state_store: Optional[StateStore] = None
        self.session_traceid: Optional[str] = None
        self.log_dir: Optional[Path] = None

    def _get_run_id(self) -> Optional[str]:
        """从pytest配置中获取run_id"""
        # 从命令行参数或配置中获取run_id
        # pytest可以通过 --run-id 参数传递，或者通过环境变量
        try:
            run_id = self.config.getoption("--run-id", default=None)
        except ValueError:
            # 如果选项不存在，尝试从环境变量获取
            run_id = None

        if not run_id:
            # 尝试从环境变量获取
            import os

            run_id = os.environ.get("PYTEST_RUN_ID")
        return run_id

    def _get_state_store(self) -> Optional[StateStore]:
        """获取状态存储实例"""
        # 这里可以从依赖注入容器获取，或者使用单例模式
        # 暂时使用全局状态存储实例
        from framework.task.state_store import MemoryStateStore

        # 注意：实际使用时应该从容器中获取，确保主进程和子进程使用同一个实例
        # 这里为了演示，使用全局单例
        if not hasattr(TaskPlugin, "_global_state_store"):
            TaskPlugin._global_state_store = MemoryStateStore()
        return TaskPlugin._global_state_store

    def _setup_logging(self) -> None:
        """设置日志"""
        if not self.run_id:
            return

        # 创建日志目录
        log_dir = Path("logs") / self.run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir

        # 配置日志文件handler
        log_file = log_dir / "pytest.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 创建自定义Formatter，支持traceid
        class TraceIdFormatter(logging.Formatter):
            """支持traceid的日志格式化器"""

            def format(self, record):
                # 从contextvars获取traceid
                traceid = get_traceid()
                record.traceid = traceid
                return super().format(record)

        formatter = TraceIdFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(traceid)s] - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # 添加到root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    @pytest.hookimpl(tryfirst=True)
    def pytest_configure(self, config):
        """初始化插件，获取run_id"""
        logger.info("pytest_configure: 初始化任务管理插件")

        # 获取run_id
        self.run_id = self._get_run_id()
        if not self.run_id:
            logger.warning("未找到run_id，任务管理功能将不可用")
            return

        logger.info(f"pytest_configure: run_id={self.run_id}")

        # 获取状态存储
        self.state_store = self._get_state_store()

        # 设置日志
        self._setup_logging()

        # 注册自定义选项
        config.addinivalue_line(
            "markers", "task_managed: 标记为任务管理的测试用例"
        )

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        """会话开始，设置traceid"""
        logger.info("pytest_sessionstart: 测试会话开始")

        if not self.run_id:
            return

        # 生成会话级别的traceid
        self.session_traceid = generate_traceid()
        set_traceid(self.session_traceid)

        logger.info(f"pytest_sessionstart: session_traceid={self.session_traceid}")

        # 更新状态为运行中
        if self.state_store:
            self.state_store.set_status(self.run_id, TaskStatus.RUNNING)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """会话结束，清理资源"""
        logger.info(f"pytest_sessionfinish: 测试会话结束，退出状态={exitstatus}")

        if not self.run_id or not self.state_store:
            return

        # 根据退出状态更新任务状态
        if exitstatus == 0:
            status = TaskStatus.COMPLETED
        else:
            status = TaskStatus.FAILED

        self.state_store.set_status(self.run_id, status)

        # 清除traceid
        clear_traceid()

        logger.info(f"pytest_sessionfinish: 任务状态已更新为 {status}")

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, config, items):
        """收集阶段检查中止标志"""
        if not self.run_id or not self.state_store:
            return

        # 检查是否已中止
        if self.state_store.check_flag(self.run_id, "cancelled"):
            logger.warning("检测到任务已中止，跳过所有测试用例")
            # 跳过所有测试用例
            for item in items:
                item.add_marker(
                    pytest.mark.skip(reason="任务已中止")
                )

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item):
        """每个测试用例开始前检查状态"""
        if not self.run_id or not self.state_store:
            return

        # 生成测试用例的traceid
        test_traceid = generate_traceid()
        set_traceid(test_traceid)

        logger.info(
            f"pytest_runtest_setup: {item.nodeid}, traceid={test_traceid}"
        )

        # 检查是否已中止
        if self.state_store.check_flag(self.run_id, "cancelled"):
            logger.warning(f"测试用例 {item.nodeid} 被跳过：任务已中止")
            pytest.skip("任务已中止")

        # 检查是否暂停，如果暂停则等待恢复
        if self.state_store.check_flag(self.run_id, "paused"):
            logger.info(f"测试用例 {item.nodeid} 等待恢复：任务已暂停")
            # 等待恢复（轮询直到暂停标志被清除）
            self.state_store.wait_for_flag(self.run_id, "paused", timeout=None)
            logger.info(f"测试用例 {item.nodeid} 继续执行：任务已恢复")

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_teardown(self, item):
        """每个测试用例结束后检查状态"""
        if not self.run_id or not self.state_store:
            return

        traceid = get_traceid()
        logger.info(f"pytest_runtest_teardown: {item.nodeid}, traceid={traceid}")

        # 再次检查是否已中止（在用例执行过程中可能被中止）
        if self.state_store.check_flag(self.run_id, "cancelled"):
            logger.warning(f"测试用例 {item.nodeid} 执行后检测到任务已中止")

        # 清除当前测试用例的traceid（可选，因为下一个用例会设置新的）
        # clear_traceid()  # 注释掉，保留traceid用于日志


def pytest_addoption(parser):
    """添加pytest命令行选项"""
    parser.addoption(
        "--run-id",
        action="store",
        default=None,
        help="测试任务的run_id，用于任务管理",
    )


def pytest_configure(config):
    """pytest配置钩子 - 注册插件"""
    # 创建插件实例并注册
    plugin = TaskPlugin(config)
    config.pluginmanager.register(plugin, "task_plugin")

