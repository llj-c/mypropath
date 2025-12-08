"""基于 httpx 的 HTTP 客户端基类"""

import asyncio
import logging
import mimetypes
from pathlib import Path
import time
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    override,
)

import httpx
from pydantic import BaseModel, ValidationError as PydanticValidationError

from framework.api.common.fw_exceptions import (
    FWAPIError,
    FWAPIRetryExhausted,
    FWValidationError,
)
from framework.api.common.model.base_data_model import BaseDataModel
from framework.config import ApiConfig
from framework.utils.file_op import check_path_exists, check_path_is_file

from .client_abc import (
    FWAsyncHttpClientABC,
    FWSyncHttpClientABC,
    RequestInterceptor,
    ResponseInterceptor,
)
from .fw_httpclient_models import FWHttpClientParams

# 类型变量，用于泛型支持
ResponseModel = TypeVar("ResponseModel", bound=BaseDataModel)

logger = logging.getLogger(__name__)


class FWHttpClientInterceptor(RequestInterceptor, ResponseInterceptor):
    """请求的前置和后置处理"""

    def make_request(self, request: httpx.Request) -> httpx.Request:
        """修改请求对象（如添加签名、日志）"""
        logger.debug(f"Request: {request.method} {request.url}")
        return request

    def make_response(self, response: httpx.Response) -> httpx.Response:
        """处理响应对象（如校验状态码、日志）"""
        logger.debug(f"Response: {response.status_code} {response.url}")
        return response


class FWHttpClient:
    """HTTP 客户端基类，基于 httpx 封装"""

    def __init__(
        self,
        api_config: ApiConfig,
        http_client_interceptor: Optional[FWHttpClientInterceptor] = None,
    ):
        """
        初始化 HTTP 客户端

        Args:
            api_config: API 配置对象
            http_client_interceptor: HTTP 客户端拦截器，用于请求和响应处理
        """
        self.config = api_config
        self.http_client_interceptor = (
            http_client_interceptor or FWHttpClientInterceptor()
        )
        # 在初始化时立即初始化参数
        self.http_client_params = FWHttpClientParams(
            base_url=self.config.api_base_url,
            timeout=self.config.api_timeout,
            headers=self.config.api_headers,
            verify=self.config.api_verify_ssl,
            follow_redirects=self.config.api_follow_redirects,
            default_encoding=self.config.api_default_encoding,
        )

    def _init_http_client_params(self):
        """重新初始化 HTTP 客户端参数（用于更新配置）"""
        self.http_client_params = FWHttpClientParams(
            base_url=self.config.api_base_url,
            timeout=self.config.api_timeout,
            headers=self.config.api_headers,
            verify=self.config.api_verify_ssl,
            follow_redirects=self.config.api_follow_redirects,
            default_encoding=self.config.api_default_encoding,
        )

    def _convert_data_to_dict(
        self,
        json_data: Optional[Union[Dict[str, Any], BaseModel]],
        data: Optional[Union[Dict[str, Any], BaseModel]],
        params: Optional[Union[Dict[str, Any], BaseModel]],
    ) -> tuple[
        Optional[Union[str, Dict[str, Any]]],
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
    ]:
        """
        将 Pydantic 模型转换为字典或 JSON 字符串

        Args:
            json_data: JSON 数据（可能是字典或 BaseModel）
            data: 表单数据（可能是字典或 BaseModel）
            params: 查询参数（可能是字典或 BaseModel）

        Returns:
            转换后的 (json_data, data, params) 元组
        """
        converted_json: Optional[Union[str, Dict[str, Any]]] = None
        converted_data: Optional[Dict[str, Any]] = None
        converted_params: Optional[Dict[str, Any]] = None

        if json_data is not None:
            if isinstance(json_data, BaseModel):
                converted_json = json_data.model_dump_json(exclude_none=True)
            else:
                converted_json = json_data

        if data is not None:
            if isinstance(data, BaseModel):
                converted_data = data.model_dump(exclude_none=True)
            else:
                converted_data = data

        if params is not None:
            if isinstance(params, BaseModel):
                converted_params = params.model_dump(exclude_none=True)
            else:
                converted_params = params

        return converted_json, converted_data, converted_params

    def _process_response(
        self,
        response: httpx.Response,
        raise_for_status: bool,
        response_model: Optional[Type[ResponseModel]] = None,
    ) -> Union[httpx.Response, ResponseModel]:
        """处理响应：应用拦截器、检查状态码、解析模型"""
        resp = self.http_client_interceptor.make_response(response)
        if raise_for_status:
            resp.raise_for_status()
        if response_model:
            return response_model.model_validate(resp.json())
        return resp

    def set_auth_token(self, token: str, token_type: str = "Bearer"):
        """
        设置认证 token

        Args:
            token: 认证 token
            token_type: token 类型，默认 "Bearer"
        """
        if not self.http_client_params.headers:
            self.http_client_params.headers = {}

        self.http_client_params.headers["Authorization"] = f"{token_type} {token}"

    def set_header(self, key: str, value: str):
        """
        设置请求头

        Args:
            key: 请求头键
            value: 请求头值
        """
        if not self.http_client_params.headers:
            self.http_client_params.headers = {}

        self.http_client_params.headers[key] = value

    def remove_header(self, key: str):
        """
        移除请求头

        Args:
            key: 请求头键
        """
        if not self.http_client_params.headers:
            return

        if key not in self.http_client_params.headers:
            return

        del self.http_client_params.headers[key]

    def get_headers(self) -> dict:
        """获取当前请求头"""
        return self.http_client_params.headers or {}

    def is_valid_fpath(self, fp: str | Path):
        return check_path_exists(fp) and check_path_is_file(fp)

    def _prepare_upload_file_params(
        self,
        file_path: Union[str, Path],
        field_name: str,
        filename: Optional[str],
        content_type: Optional[str],
        data: Optional[Dict[str, Any]],
    ) -> Tuple[Path, str, str, Dict[str, Any]]:
        """
        准备文件上传的参数（公共逻辑）

        Args:
            file_path: 文件路径
            field_name: 表单字段名
            filename: 文件名（可选）
            content_type: 文件 MIME 类型（可选）
            data: 额外的表单数据

        Returns:
            (file_path_obj, filename, content_type, form_data) 元组
        """
        file_path_obj = Path(file_path)

        if not self.is_valid_fpath(file_path_obj):
            raise FWAPIError(f"文件不存在或者不是文件:{file_path_obj}")

        # 确定文件名
        if filename is None:
            filename = file_path_obj.name

        # 确定 content_type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(file_path_obj))
            if content_type is None:
                content_type = "application/octet-stream"

        # 合并额外的表单数据
        form_data = data.copy() if data else {}

        return file_path_obj, filename, content_type, form_data

    def _prepare_download_file_path(self, save_path: Union[str, Path]) -> Path:
        """
        准备下载文件的保存路径（公共逻辑）

        Args:
            save_path: 保存路径

        Returns:
            Path 对象
        """
        save_path_obj = Path(save_path)
        # 确保父目录存在
        save_path_obj.parent.mkdir(parents=True, exist_ok=True)
        return save_path_obj

    def _validate_download_response(
        self, response: Union[httpx.Response, Any]
    ) -> httpx.Response:
        """
        验证下载响应（公共逻辑）

        Args:
            response: HTTP 响应

        Returns:
            httpx.Response 对象

        Raises:
            ValueError: 如果响应不是 httpx.Response 类型
        """
        if not isinstance(response, httpx.Response):
            raise ValueError("下载文件时不能使用 response_model，请使用原始响应")
        return response

    def _update_httpx_client_headers(
        self, httpx_client: Optional[Union[httpx.Client, httpx.AsyncClient]]
    ):
        """
        更新 httpx 客户端的 headers（公共逻辑）

        Args:
            httpx_client: httpx 客户端对象（同步或异步）
        """
        if httpx_client:
            httpx_client.headers.update(self.get_headers())

    def _remove_httpx_client_header(
        self, httpx_client: Optional[Union[httpx.Client, httpx.AsyncClient]], key: str
    ):
        """
        从 httpx 客户端移除指定的 header（公共逻辑）

        Args:
            httpx_client: httpx 客户端对象（同步或异步）
            key: 要移除的 header 键
        """
        if httpx_client:
            httpx_client.headers.pop(key, None)

    def _prepare_request(
        self,
        httpx_client: httpx.Client | httpx.AsyncClient,
        url: str,
        method: str,
        params: Optional[Union[Dict[str, Any], BaseModel]],
        json_data: Optional[Union[Dict[str, Any], BaseModel]],
        data: Optional[Union[Dict[str, Any], BaseModel]],
        files: Optional[Union[Dict[str, Any], List[Tuple[str, Any]]]],
    ) -> httpx.Request:
        # 转换数据格式
        converted_json, converted_data, converted_params = self._convert_data_to_dict(
            json_data, data, params
        )

        _request = httpx_client.build_request(
            method=method.upper(),
            url=url,
            params=converted_params,
            json=converted_json,
            data=converted_data,
            files=files,
            headers=self.get_headers(),
        )

        return self.http_client_interceptor.make_request(_request)


class FWSyncHttpClient(FWHttpClient, FWSyncHttpClientABC):
    """同步 HTTP 客户端"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.httpx_client: httpx.Client = self.build_httpx_client()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def close(self):
        """关闭客户端连接"""
        if self.httpx_client:
            self.httpx_client.close()

    def build_httpx_client(self) -> httpx.Client:
        """构建 httpx 同步客户端"""
        return httpx.Client(**self.http_client_params.model_dump(exclude_none=True))

    def make_request(
        self,
        url: str,
        method: str,
        params: Optional[Union[Dict[str, Any], BaseModel]],
        json_data: Optional[Union[Dict[str, Any], BaseModel]],
        data: Optional[Union[Dict[str, Any], BaseModel]],
        files: Optional[Union[Dict[str, Any], List[Tuple[str, Any]]]] = None,
        raise_for_status: bool = True,
        response_model: Optional[Type[ResponseModel]] = None,
    ) -> Union[httpx.Response, ResponseModel]:
        """发送 HTTP 请求"""
        request = self._prepare_request(
            self.httpx_client,
            url=url,
            method=method.upper(),
            params=params,
            json_data=json_data,
            data=data,
            files=files,
        )
        return self.retry_request(
            lambda: self.httpx_client.send(request),
            raise_for_status,
            response_model,
        )

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        raise_for_status: bool = False,
        **kwargs,
    ) -> Union[httpx.Response, ResponseModel]:
        return self.make_request(
            url=url,
            method="GET",
            params=params,
            json_data=None,
            data=None,
            files=None,
            raise_for_status=raise_for_status,
            response_model=response_model,
            **kwargs,
        )

    def post(
        self,
        url: str,
        json: Optional[Union[Dict[str, Any], BaseModel]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Union[Dict[str, Any], List[Tuple[str, Any]]]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Union[httpx.Response, ResponseModel]:
        return self.make_request(
            url,
            "POST",
            None,
            json,
            data,
            files,
            raise_for_status,
            response_model,
            **kwargs,
        )

    def retry_request(
        self,
        request_func: Callable[[], httpx.Response],
        raise_for_status: bool,
        response_model: Optional[Type[ResponseModel]] = None,
    ) -> Union[httpx.Response, ResponseModel]:
        """
        执行请求并处理重试逻辑

        Args:
            request_func: 请求函数
            raise_for_status: 是否在状态码错误时抛出异常
            response_model: 响应模型类型

        Returns:
            httpx.Response 或解析后的响应模型
        """
        if not callable(request_func):
            raise ValueError("request_func must be a callable")

        if self.config.api_retry_times <= 0:
            return self._process_response(
                request_func(), raise_for_status, response_model
            )

        retry_count = 0
        last_exception = None
        while retry_count < self.config.api_retry_times:
            try:
                _resp = request_func()
                return self._process_response(_resp, raise_for_status, response_model)
            except PydanticValidationError as e:
                raise FWValidationError(
                    f"解析响应数据失败: {traceback.format_exc()}"
                ) from e
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                retry_count += 1
                if retry_count >= self.config.api_retry_times:
                    raise FWAPIRetryExhausted(
                        message=f"{e.__class__.__name__}:重试次数耗尽: {traceback.format_exc()}",
                    ) from e
                logger.warning(
                    f"请求失败, 继续重试 ({retry_count}/{self.config.api_retry_times}): {e}"
                )
                time.sleep(self.config.api_retry_delay)
            except httpx.HTTPStatusError as e:
                # 根据配置决定是否重试状态码错误
                if e.response.status_code in self.config.api_retry_status_codes:
                    last_exception = e
                    retry_count += 1
                    if retry_count >= self.config.api_retry_times:
                        raise FWAPIRetryExhausted(
                            message=f"HTTP状态码错误重试次数耗尽: {e.response.status_code}"
                        ) from e
                    logger.warning(
                        f"HTTP状态码错误 {e.response.status_code}, 继续重试 ({retry_count}/{self.config.api_retry_times})"
                    )
                    time.sleep(self.config.api_retry_delay)
                else:
                    # 不在重试列表中的状态码错误，直接抛出
                    raise
            except Exception as e:
                raise FWAPIError(
                    f"请求出现非预期异常,终止重试: {traceback.format_exc()}"
                ) from e

        if last_exception:
            raise FWAPIRetryExhausted(
                message=f"{last_exception.__class__.__name__}:重试次数耗尽: {traceback.format_exc()}",
            ) from last_exception
        raise FWAPIRetryExhausted(message="重试次数耗尽")

    @override
    def set_auth_token(self, token: str, token_type: str = "Bearer"):
        """设置认证 token（同步方法）"""
        super().set_auth_token(token, token_type)
        self._update_httpx_client_headers(self.httpx_client)

    @override
    def set_header(self, key: str, value: str):
        """设置请求头（同步方法）"""
        super().set_header(key, value)
        self._update_httpx_client_headers(self.httpx_client)

    @override
    def remove_header(self, key: str):
        """移除请求头（同步方法）"""
        super().remove_header(key)
        self._remove_httpx_client_header(self.httpx_client, key)

    @override
    def upload_file(
        self,
        url: str,
        file_path: Union[str, Path],
        field_name: str = "file",
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Union[httpx.Response, Any]:
        """
        上传文件（同步方法）

        Args:
            url: 上传 URL
            file_path: 文件路径
            field_name: 表单字段名，默认为 "file"
            filename: 文件名（可选，默认使用 file_path 的文件名）
            content_type: 文件 MIME 类型（可选，自动推断）
            data: 额外的表单数据
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数

        Returns:
            httpx.Response 或解析后的响应模型
        """
        file_path_obj, filename, content_type, form_data = (
            self._prepare_upload_file_params(
                file_path, field_name, filename, content_type, data
            )
        )

        with file_path_obj.open("rb") as f:
            files = {field_name: (filename, f, content_type)}
            return self.post(
                url=url,
                data=form_data,
                files=files,
                raise_for_status=raise_for_status,
                **kwargs,
            )

    @override
    def download_file(
        self,
        url: str,
        save_path: Union[str, Path],
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 8192,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Path:
        """
        下载文件并保存到本地（同步方法）

        Args:
            url: 下载 URL
            save_path: 保存路径
            params: 查询参数
            chunk_size: 下载块大小（字节），默认 8192
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数

        Returns:
            保存的文件路径
        """
        save_path_obj = self._prepare_download_file_path(save_path)

        # 使用流式下载
        response = self.get(
            url=url,
            params=params,
            raise_for_status=raise_for_status,
            **kwargs,
        )

        response = self._validate_download_response(response)

        # 流式写入文件
        with open(save_path_obj, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        return save_path_obj


class FWAsyncHttpClient(FWHttpClient, FWAsyncHttpClientABC):
    """异步 HTTP 客户端"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.httpx_client: httpx.AsyncClient = self.build_httpx_client()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.aclose()

    async def aclose(self):
        """异步关闭客户端连接"""
        if self.httpx_client:
            await self.httpx_client.aclose()

    def build_httpx_client(self) -> httpx.AsyncClient:
        """构建 httpx 异步客户端"""
        return httpx.AsyncClient(
            **self.http_client_params.model_dump(exclude_none=True)
        )

    async def make_request(
        self,
        url: str,
        method: str,
        params: Optional[Union[Dict[str, Any], BaseModel]],
        json_data: Optional[Union[Dict[str, Any], BaseModel]],
        data: Optional[Union[Dict[str, Any], BaseModel]],
        files: Optional[Union[Dict[str, Any], List[Tuple[str, Any]]]] = None,
        raise_for_status: bool = True,
        response_model: Optional[Type[ResponseModel]] = None,
    ) -> Union[httpx.Response, ResponseModel]:
        """发送 HTTP 请求（异步）"""
        request = self._prepare_request(
            self.httpx_client,
            url=url,
            method=method.upper(),
            params=params,
            json_data=json_data,
            data=data,
            files=files,
        )
        return await self.retry_request(
            request,
            raise_for_status,
            response_model,
        )

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        raise_for_status: bool = False,
        **kwargs,
    ) -> Union[httpx.Response, ResponseModel]:
        return await self.make_request(
            url=url,
            method="GET",
            params=params,
            json_data=None,
            data=None,
            files=None,
            raise_for_status=raise_for_status,
            response_model=response_model,
            **kwargs,
        )

    async def post(
        self,
        url: str,
        json: Optional[Union[Dict[str, Any], BaseModel]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Union[Dict[str, Any], List[Tuple[str, Any]]]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Union[httpx.Response, ResponseModel]:
        return await self.make_request(
            url,
            "POST",
            None,
            json,
            data,
            files,
            raise_for_status,
            response_model,
            **kwargs,
        )

    @override
    def set_auth_token(self, token: str, token_type: str = "Bearer"):
        """设置认证 token（同步方法，异步客户端中也可使用）"""
        super().set_auth_token(token, token_type)
        self._update_httpx_client_headers(self.httpx_client)

    @override
    def set_header(self, key: str, value: str):
        """设置请求头（同步方法，异步客户端中也可使用）"""
        super().set_header(key, value)
        self._update_httpx_client_headers(self.httpx_client)

    @override
    def remove_header(self, key: str):
        """移除请求头（同步方法，异步客户端中也可使用）"""
        super().remove_header(key)
        self._remove_httpx_client_header(self.httpx_client, key)

    @override
    async def upload_file(
        self,
        url: str,
        file_path: Union[str, Path],
        field_name: str = "file",
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Union[httpx.Response, Any]:
        """
        上传文件（异步方法）

        Args:
            url: 上传 URL
            file_path: 文件路径
            field_name: 表单字段名，默认为 "file"
            filename: 文件名（可选，默认使用 file_path 的文件名）
            content_type: 文件 MIME 类型（可选，自动推断）
            data: 额外的表单数据
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数

        Returns:
            httpx.Response 或解析后的响应模型
        """
        file_path_obj, filename, content_type, form_data = (
            self._prepare_upload_file_params(
                file_path, field_name, filename, content_type, data
            )
        )

        with file_path_obj.open("rb") as f:
            files = {field_name: (filename, f, content_type)}
            return await self.post(
                url=url,
                data=form_data,
                files=files,
                raise_for_status=raise_for_status,
                **kwargs,
            )

    @override
    async def download_file(
        self,
        url: str,
        save_path: Union[str, Path],
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 8192,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Path:
        """
        下载文件并保存到本地（异步方法）

        Args:
            url: 下载 URL
            save_path: 保存路径
            params: 查询参数
            chunk_size: 下载块大小（字节），默认 8192
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数

        Returns:
            保存的文件路径
        """
        save_path_obj = self._prepare_download_file_path(save_path)

        # 使用流式下载
        response = await self.get(
            url=url,
            params=params,
            raise_for_status=raise_for_status,
            **kwargs,
        )

        response = self._validate_download_response(response)

        # 流式写入文件
        with open(save_path_obj, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        return save_path_obj

    async def retry_request(
        self,
        request: httpx.Request,
        raise_for_status: bool,
        response_model: Optional[Type[ResponseModel]] = None,
    ) -> Union[httpx.Response, ResponseModel]:
        """
        执行请求并处理重试逻辑（异步）

        Args:
            request: httpx 请求对象
            raise_for_status: 是否在状态码错误时抛出异常
            response_model: 响应模型类型

        Returns:
            httpx.Response 或解析后的响应模型
        """
        if self.config.api_retry_times <= 0:
            _resp = await self.httpx_client.send(request)
            return self._process_response(_resp, raise_for_status, response_model)

        retry_count = 0
        last_exception = None
        while retry_count < self.config.api_retry_times:
            try:
                _resp = await self.httpx_client.send(request)
                return self._process_response(_resp, raise_for_status, response_model)
            except PydanticValidationError as e:
                raise FWValidationError(
                    f"解析响应数据失败: {traceback.format_exc()}"
                ) from e
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                retry_count += 1
                if retry_count >= self.config.api_retry_times:
                    raise FWAPIRetryExhausted(
                        message=f"{e.__class__.__name__}:重试次数耗尽: {traceback.format_exc()}",
                    ) from e
                logger.warning(
                    f"请求失败, 继续重试 ({retry_count}/{self.config.api_retry_times}): {e}"
                )
                await asyncio.sleep(self.config.api_retry_delay)
            except httpx.HTTPStatusError as e:
                # 根据配置决定是否重试状态码错误
                if e.response.status_code in self.config.api_retry_status_codes:
                    last_exception = e
                    retry_count += 1
                    if retry_count >= self.config.api_retry_times:
                        raise FWAPIRetryExhausted(
                            message=f"HTTP状态码错误重试次数耗尽: {e.response.status_code}"
                        ) from e
                    logger.warning(
                        f"HTTP状态码错误 {e.response.status_code}, 继续重试 ({retry_count}/{self.config.api_retry_times})"
                    )
                    await asyncio.sleep(self.config.api_retry_delay)
                else:
                    # 不在重试列表中的状态码错误，直接抛出
                    raise
            except Exception as e:
                raise FWAPIError(
                    f"请求出现非预期异常,终止重试: {traceback.format_exc()}"
                ) from e

        if last_exception:
            raise FWAPIRetryExhausted(
                message=f"{last_exception.__class__.__name__}:重试次数耗尽: {traceback.format_exc()}",
            ) from last_exception
        raise FWAPIRetryExhausted(message="重试次数耗尽")
