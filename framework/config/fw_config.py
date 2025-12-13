
from framework.config.api_config import ApiConfig
from framework.config.db_config import DatabaseConfig
from framework.config.fw_base_settings import FWBaseSettings
from pydantic import Field


class FWConfig(FWBaseSettings):

    app_host: str = Field(default="localhost", description="应用主机地址")
    app_port: int = Field(default=48081, description="应用端口")

    api: ApiConfig
    database: DatabaseConfig
