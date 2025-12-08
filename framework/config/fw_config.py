from .api_config import ApiConfig
from .db_config import DatabaseConfig


class FWConfig:

    def __init__(self):
        self.api_config = ApiConfig()  # type: ignore
        self.db_config = DatabaseConfig()  # type: ignore
