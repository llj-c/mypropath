
from framework.config.api_config import ApiConfig
from framework.config.db_config import DatabaseConfig
from framework.config.fw_base_settings import FWBaseSettings


class FWConfig(FWBaseSettings):

    api: ApiConfig
    database: DatabaseConfig
