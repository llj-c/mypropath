from framework.api.common.model import BaseDataModel
from typing import Optional
import httpx
from pydantic import Field


class FWHttpClientParams(BaseDataModel):

    params: Optional[dict] = Field(default=None, description="请求参数")
    headers: Optional[dict] = Field(default=None, description="请求头")
    cookies: Optional[dict] = Field(default=None, description="请求cookie")
    verify: Optional[bool] = Field(default=True, description="是否验证SSL证书")
    cert: Optional[dict] = Field(default=None, description="证书")
    timeout: Optional[float] = Field(default=None, description="请求超时时间")
    follow_redirects: Optional[bool] = Field(default=False, description="是否跟随重定向")
    max_redirects: Optional[int] = Field(default=None, description="最大重定向次数")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    default_encoding: Optional[str] = Field(default=None, description="默认编码")
    # trust_env: Optional[bool] = Field(default=True, description="是否信任环境变量")
    # http1: Optional[bool] = Field(default=True, description="是否使用HTTP/1.1")
    # http2: Optional[bool] = Field(default=False, description="是否使用HTTP/2")
    # proxy: Optional[dict] = Field(default=None, description="代理")
    # mounts: Optional[dict] = Field(default=None, description="挂载")
