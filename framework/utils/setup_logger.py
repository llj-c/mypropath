import logging


class LoggerManager:
    _instance = None

    def __init__(self) -> None:
        pass

    def setup_logger(self, name: str | None = None):
        if self._instance is not None:
            return self._instance

        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        # 4. 配置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'  # 补充时间格式，日志更易读
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 5. 配置文件处理器（添加utf-8编码，避免中文乱码）
        file_handler = logging.FileHandler('logs/pytest.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(  # 格式和控制台一致，也可按需差异化
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.propagate = False

        return logger
