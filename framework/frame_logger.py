from framework.task.traceid import get_traceid
from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path


class FrameLogger:

    def _init_framework_logger(self) -> logging.Logger:
        # 1. 获取框架日志器（统一挂载 Handler，子 logger 透传即可）
        logger = logging.getLogger("framework")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 继续向 root 透传，让 pytest 聚合
        framework_log_file = Path("logs/framework.log")

        # 2. 避免重复添加Handler
        if logger.handlers:
            return logger

        # 3. 固定路径的文件Handler（日志轮转，避免文件过大）
        framework_log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            framework_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB/文件
            backupCount=5,              # 保留5个备份
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)

        # 4. 日志格式（支持traceid）
        class TraceIdFormatter(logging.Formatter):
            def format(self, record):
                record.traceid = get_traceid()
                return super().format(record)

        formatter = TraceIdFormatter("%(asctime)s - %(name)s - %(levelname)s - [%(traceid)s] - %(message)s")
        file_handler.setFormatter(formatter)

        # 5. 添加Handler
        logger.addHandler(file_handler)
        logger.info(f"框架日志器初始化完成（固定路径）：{framework_log_file.absolute()}")

        return logger

    def get_framework_logger(self) -> logging.Logger:
        return self._init_framework_logger()


frame_logger = FrameLogger().get_framework_logger()