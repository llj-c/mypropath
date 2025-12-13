from pydantic import Field, field_validator, ValidationError as PydanticValidationError
from pydantic import BaseModel, ConfigDict


class ApiConfig(BaseModel):

    model_config = ConfigDict(
        extra="ignore",
    )

    base_url: str = Field(..., description="接口基础域名")
    timeout: float = Field(..., description="请求超时时间")
    verify_ssl: bool = Field(..., description="是否验证SSL证书")
    follow_redirects: bool = Field(..., description="是否跟随重定向")
    retry_times: int = Field(..., description="重试次数")
    retry_delay: float = Field(..., description="重试延迟时间")
    retry_status_codes: list[int] = Field(
        default_factory=list, description="重试状态码, 只有符合这些状态码的请求才会重试")
    default_encoding: str = Field(default="utf-8", description="默认编码")

    @field_validator('retry_status_codes')
    def validate_retry_status_codes(cls, v):
        if isinstance(v, str):
            return [int(code) for code in v.split(',')]
        elif isinstance(v, list):
            return v
        raise PydanticValidationError("retry_status_codes 必须是一个字符串或列表")
