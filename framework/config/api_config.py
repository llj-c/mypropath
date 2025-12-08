from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource, PydanticBaseSettingsSource
from pydantic import Field


class ApiConfig(BaseSettings):

    # 环境变量前缀为FW_API_（避免与其他配置冲突）
    model_config = SettingsConfigDict(
        env_prefix="FW_API_",
        toml_file='framework/config/config_files/api_config.toml'
    )

    api_base_url: str = Field(..., description="接口基础域名")
    api_timeout: float = Field(..., description="请求超时时间")
    api_headers: dict = Field(default_factory=dict, description="请求头")
    api_verify_ssl: bool = Field(..., description="是否验证SSL证书")
    api_follow_redirects: bool = Field(..., description="是否跟随重定向")
    api_retry_times: int = Field(..., description="重试次数")
    api_retry_delay: float = Field(..., description="重试延迟时间")
    api_retry_status_codes: list[int] = Field(
        default_factory=list, description="重试状态码, 只有符合这些状态码的请求才会重试")
    api_default_encoding: str = Field(default="utf-8", description="默认编码")

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """自定义配置来源, 优先级: 环境变量 > 初始设置 > TOML文件"""
        return (env_settings, init_settings,
                TomlConfigSettingsSource(settings_cls))
