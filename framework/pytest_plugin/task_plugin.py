"""pytest任务管理插件 - 实现任务状态检查、暂停/中止控制等功能"""

import logging
from pathlib import Path
from re import DEBUG
from typing import Optional

import pytest
import uuid

from framework.task.traceid import (

    get_traceid,

)


class TaskPlugin:
    """pytest任务管理插件"""

    def __init__(self, config):
        """初始化插件"""
        self.config = config
        self.run_id: Optional[str] = None
        self.session_traceid: Optional[str] = None
        self.log_dir: Optional[Path] = None

    def _get_run_id(self) -> Optional[str]:
        """从pytest配置中获取run_id"""
        # 从命令行参数或配置中获取run_id
        # pytest可以通过 --run-id 参数传递，或者通过环境变量

        run_id = self.config.getoption("--run-id", default=None)
        if not run_id:
            run_id = str(uuid.uuid4())

        self.config.run_id = run_id
        self.run_id = run_id
        return run_id

    def _setup_logging(self) -> None:
        """设置日志"""
   
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()
        root_logger.propagate = False
        pytest_file_handler = self.get_file_handler(self.get_pytest_file_log_path())
        console_handler = self.get_console_handler()
        root_logger.addHandler(pytest_file_handler)

        framework_logger = logging.getLogger("framework")
        framework_logger.setLevel(logging.DEBUG)
        framework_logger.handlers.clear()
        framework_logger.propagate = True
        framework_logger.addHandler(self.get_file_handler(Path("logs/framework.log")))

        # 初始化test，透传上去
        test_logger = logging.getLogger("test")
        test_logger.setLevel(logging.DEBUG)
        test_logger.handlers.clear()
        test_logger.addHandler(console_handler)
        test_logger.propagate = True
        

    def get_console_handler(self):
        # 配置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'  # 补充时间格式，日志更易读
        )
        console_handler.setFormatter(console_formatter)
        return console_handler

    def get_file_handler(self, filepath: Path):

        filepath.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(filepath, encoding="utf-8")
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
        return file_handler

    def get_pytest_file_log_path(self):
        run_id = self._get_run_id()
        return Path("logs").joinpath(str(run_id)).joinpath("pytest.log")
