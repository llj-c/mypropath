from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FW_DB_",
        toml_file="framework/config/config_files/db_config.toml",
    )

    host: str = Field(..., description="数据库主机地址")
    port: int = Field(default=3306, description="数据库端口")
    username: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: str = Field(..., description="数据库名称")
    charset: str = Field(default="utf8mb4", description="数据库字符集")
    echo: bool = Field(default=False, description="是否打印SQL语句")
    pool_size: int = Field(default=5, description="连接池大小")
    max_overflow: int = Field(default=10, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="获取连接超时时间（秒）")
    pool_recycle: int = Field(default=1800, description="连接回收时间（秒）")
    pool_pre_ping: bool = Field(default=True, description="是否启用预检测")

    def build_connection_url(self) -> str:
        """生成 SQLAlchemy 兼容的连接串."""
        username = quote_plus(self.username)
        password = quote_plus(self.password)
        return (
            f"mysql+pymysql://{username}:{password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?charset={self.charset}"
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """自定义配置来源, 优先级: 环境变量 > 初始化参数 > TOML 文件."""
        return (
            env_settings,
            init_settings,
            TomlConfigSettingsSource(settings_cls),
        )

