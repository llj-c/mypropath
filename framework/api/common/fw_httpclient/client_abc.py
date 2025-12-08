import httpx
from typing import Protocol, Any, Dict, Optional, Type, TypeVar, Union, List, Tuple, Awaitable
from abc import ABC, abstractmethod
from pydantic import BaseModel
from pathlib import Path

from framework.api.common.model.base_data_model import BaseDataModel

# 类型变量，用于泛型支持（与 fw_httpclient.py 中的定义保持一致）
ResponseModel = TypeVar("ResponseModel", bound=BaseDataModel)


class RequestInterceptor(Protocol):
    """请求拦截器（前置处理）"""

    def make_request(self, request: httpx.Request) -> httpx.Request:
        ...


class ResponseInterceptor(Protocol):
    """响应拦截器（后置处理）"""

    def make_response(self, response: httpx.Response) -> httpx.Response:
        ...


class FWSyncHttpClientABC(ABC):
    """同步 HTTP 客户端抽象基类，定义同步客户端必须实现的接口"""

    @abstractmethod
    def build_httpx_client(self) -> httpx.Client:
        """
        构建 httpx 同步客户端实例
        
        Returns:
            httpx 同步客户端
        """
        ...

    @abstractmethod
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
        """
        发送 HTTP 请求（同步）
        
        Args:
            url: 请求 URL
            method: HTTP 方法
            params: 查询参数
            json_data: JSON 数据
            data: 表单数据
            files: 文件上传数据，支持字典或元组列表格式
                   - 字典格式: {"file": open("path", "rb")} 或 {"file": ("filename.txt", open("path", "rb"), "text/plain")}
                   - 元组列表格式: [("file", open("path", "rb"))] 或 [("file", ("filename.txt", open("path", "rb"), "text/plain"))]
            raise_for_status: 是否在状态码错误时抛出异常
            response_model: 响应模型类型
            
        Returns:
            httpx.Response 或解析后的响应模型
        """
        ...

    @abstractmethod
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Union[httpx.Response, ResponseModel]:
        """
        发送 GET 请求（同步）
        
        Args:
            url: 请求 URL
            params: 查询参数
            response_model: 响应模型类型
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数
            
        Returns:
            httpx.Response 或解析后的响应模型
        """
        ...

    @abstractmethod
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
        """
        发送 POST 请求（同步）
        
        Args:
            url: 请求 URL
            json: JSON 数据
            data: 表单数据
            files: 文件上传数据，支持字典或元组列表格式
                   - 字典格式: {"file": open("path", "rb")} 或 {"file": ("filename.txt", open("path", "rb"), "text/plain")}
                   - 元组列表格式: [("file", open("path", "rb"))] 或 [("file", ("filename.txt", open("path", "rb"), "text/plain"))]
            response_model: 响应模型类型
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数
            
        Returns:
            httpx.Response 或解析后的响应模型
        """
        ...

    @abstractmethod
    def set_auth_token(self, token: str, token_type: str = "Bearer") -> None:
        """
        设置认证 token
        
        Args:
            token: 认证 token
            token_type: token 类型，默认 "Bearer"
        """
        ...

    @abstractmethod
    def set_header(self, key: str, value: str) -> None:
        """
        设置请求头
        
        Args:
            key: 请求头键
            value: 请求头值
        """
        ...

    @abstractmethod
    def remove_header(self, key: str) -> None:
        """
        移除请求头
        
        Args:
            key: 请求头键
        """
        ...

    @abstractmethod
    def get_headers(self) -> dict:
        """
        获取当前请求头
        
        Returns:
            请求头字典
        """
        ...

    @abstractmethod
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
        上传文件（同步）
        
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
        ...

    @abstractmethod
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
        下载文件并保存到本地（同步）
        
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
        ...


class FWAsyncHttpClientABC(ABC):
    """异步 HTTP 客户端抽象基类，定义异步客户端必须实现的接口"""

    @abstractmethod
    def build_httpx_client(self) -> httpx.AsyncClient:
        """
        构建 httpx 异步客户端实例
        
        Returns:
            httpx 异步客户端
        """
        ...

    @abstractmethod
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
        """
        发送 HTTP 请求（异步）
        
        Args:
            url: 请求 URL
            method: HTTP 方法
            params: 查询参数
            json_data: JSON 数据
            data: 表单数据
            files: 文件上传数据，支持字典或元组列表格式
                   - 字典格式: {"file": open("path", "rb")} 或 {"file": ("filename.txt", open("path", "rb"), "text/plain")}
                   - 元组列表格式: [("file", open("path", "rb"))] 或 [("file", ("filename.txt", open("path", "rb"), "text/plain"))]
            raise_for_status: 是否在状态码错误时抛出异常
            response_model: 响应模型类型
            
        Returns:
            httpx.Response 或解析后的响应模型
        """
        ...

    @abstractmethod
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        raise_for_status: bool = True,
        **kwargs,
    ) -> Union[httpx.Response, ResponseModel]:
        """
        发送 GET 请求（异步）
        
        Args:
            url: 请求 URL
            params: 查询参数
            response_model: 响应模型类型
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数
            
        Returns:
            httpx.Response 或解析后的响应模型
        """
        ...

    @abstractmethod
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
        """
        发送 POST 请求（异步）
        
        Args:
            url: 请求 URL
            json: JSON 数据
            data: 表单数据
            files: 文件上传数据，支持字典或元组列表格式
                   - 字典格式: {"file": open("path", "rb")} 或 {"file": ("filename.txt", open("path", "rb"), "text/plain")}
                   - 元组列表格式: [("file", open("path", "rb"))] 或 [("file", ("filename.txt", open("path", "rb"), "text/plain"))]
            response_model: 响应模型类型
            raise_for_status: 是否在状态码错误时抛出异常
            **kwargs: 其他参数
            
        Returns:
            httpx.Response 或解析后的响应模型
        """
        ...

    @abstractmethod
    def set_auth_token(self, token: str, token_type: str = "Bearer") -> None:
        """
        设置认证 token
        
        Args:
            token: 认证 token
            token_type: token 类型，默认 "Bearer"
        """
        ...

    @abstractmethod
    def set_header(self, key: str, value: str) -> None:
        """
        设置请求头
        
        Args:
            key: 请求头键
            value: 请求头值
        """
        ...

    @abstractmethod
    def remove_header(self, key: str) -> None:
        """
        移除请求头
        
        Args:
            key: 请求头键
        """
        ...

    @abstractmethod
    def get_headers(self) -> dict:
        """
        获取当前请求头
        
        Returns:
            请求头字典
        """
        ...

    @abstractmethod
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
        上传文件（异步）
        
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
        ...

    @abstractmethod
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
        下载文件并保存到本地（异步）
        
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
        ...