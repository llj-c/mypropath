# API 公共模块使用指南

本模块提供了基于 `httpx` 的 HTTP 客户端封装，用于自动化测试中的接口请求。

## 核心组件

### 1. BaseClient - HTTP 客户端基类

`BaseClient` 是基于 `httpx` 封装的 HTTP 客户端，提供了完整的 HTTP 请求功能。

#### 基本使用

```python
from framework.api.common import BaseClient

# 创建客户端实例
client = BaseClient(base_url="https://api.example.com")

# 发送 GET 请求
response = client.get("/api/users/1")
print(response.json())

# 关闭客户端（或使用上下文管理器）
client.close()
```

#### 使用上下文管理器

```python
from framework.api.common import BaseClient

with BaseClient(base_url="https://api.example.com") as client:
    response = client.get("/api/users/1")
    print(response.json())
```

#### 配置选项

```python
client = BaseClient(
    base_url="https://api.example.com",
    timeout=30.0,              # 请求超时时间（秒）
    headers={"X-Custom-Header": "value"},  # 默认请求头
    verify=True,               # 是否验证 SSL 证书
    follow_redirects=True,     # 是否跟随重定向
    max_retries=3,            # 最大重试次数
)
```

#### 认证

```python
# 设置 Bearer Token
client.set_auth_token("your-token-here")

# 设置自定义 Token 类型
client.set_auth_token("your-token", token_type="Custom")

# 设置自定义请求头
client.set_header("X-API-Key", "your-api-key")

# 移除请求头
client.remove_header("X-API-Key")
```

#### HTTP 方法

```python
# GET 请求
response = client.get("/api/users", params={"page": 1, "limit": 10})

# POST 请求（使用字典）
response = client.post("/api/users", json={"name": "John", "email": "john@example.com"})

# POST 请求（使用 Pydantic 模型）
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str

user_data = UserCreate(name="John", email="john@example.com")
response = client.post("/api/users", json=user_data)

# PUT 请求
response = client.put("/api/users/1", json={"name": "Jane"})

# PATCH 请求
response = client.patch("/api/users/1", json={"name": "Jane"})

# DELETE 请求
response = client.delete("/api/users/1")
```

#### 使用响应模型（Pydantic）

```python
from pydantic import BaseModel
from framework.api.common import BaseClient
from framework.utils.abstract.base_data_model import BaseDataModel

# 定义响应模型
class UserResponse(BaseDataModel):
    id: int
    name: str
    email: str
    created_at: str

# 使用响应模型自动解析
client = BaseClient(base_url="https://api.example.com")
user = client.get("/api/users/1", response_model=UserResponse)

# user 是 UserResponse 实例，可以直接访问属性
print(user.id)
print(user.name)
print(user.email)
```

#### 错误处理

```python
from framework.api.common import (
    BaseClient,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    ServerError,
    TimeoutError,
)

client = BaseClient(base_url="https://api.example.com")

try:
    response = client.get("/api/users/1")
except AuthenticationError as e:
    print(f"认证失败: {e.message}, 状态码: {e.status_code}")
except NotFoundError as e:
    print(f"资源未找到: {e.message}")
except ValidationError as e:
    print(f"数据验证失败: {e.message}, 响应数据: {e.response_data}")
except TimeoutError as e:
    print(f"请求超时: {e.message}")
except ServerError as e:
    print(f"服务器错误: {e.message}")
```

#### 不抛出异常（手动处理状态码）

```python
# 设置 raise_for_status=False，不会自动抛出异常
response = client.get("/api/users/1", raise_for_status=False)

if response.status_code == 200:
    print("请求成功")
    data = response.json()
elif response.status_code == 404:
    print("资源未找到")
else:
    print(f"其他错误: {response.status_code}")
```

### 2. 自定义异常类

模块提供了以下异常类：

- `APIError`: 基础异常类
- `AuthenticationError`: 认证错误（401）
- `NotFoundError`: 资源未找到（404）
- `ValidationError`: 数据验证错误（400-499，排除 401、404）
- `TimeoutError`: 请求超时
- `ServerError`: 服务器错误（500+）

## 继承 BaseClient 创建专用客户端

```python
from framework.api.common import BaseClient
from pydantic import BaseModel
from framework.utils.abstract.base_data_model import BaseDataModel

# 定义数据模型
class User(BaseDataModel):
    id: int
    name: str
    email: str

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

# 创建专用客户端
class UserClient(BaseClient):
    """用户 API 客户端"""
    
    def __init__(self, base_url: str, **kwargs):
        super().__init__(base_url, **kwargs)
        self.endpoint = "/api/users"
    
    def get_user(self, user_id: int) -> User:
        """获取用户信息"""
        return self.get(f"{self.endpoint}/{user_id}", response_model=User)
    
    def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        return self.post(self.endpoint, json=user_data, response_model=User)
    
    def update_user(self, user_id: int, user_data: UserCreate) -> User:
        """更新用户"""
        return self.put(f"{self.endpoint}/{user_id}", json=user_data, response_model=User)
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        response = self.delete(f"{self.endpoint}/{user_id}")
        return response.status_code == 200

# 使用示例
with UserClient(base_url="https://api.example.com") as client:
    client.set_auth_token("your-token")
    
    # 创建用户
    new_user = client.create_user(UserCreate(
        name="John",
        email="john@example.com",
        password="secret123"
    ))
    
    # 获取用户
    user = client.get_user(new_user.id)
    print(f"用户: {user.name}, 邮箱: {user.email}")
```

## 在 pytest 中使用

```python
import pytest
from framework.api.common import BaseClient

@pytest.fixture
def api_client():
    """创建 API 客户端 fixture"""
    client = BaseClient(base_url="https://api.example.com")
    client.set_auth_token("test-token")
    yield client
    client.close()

def test_get_user(api_client):
    """测试获取用户"""
    response = api_client.get("/api/users/1")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data

def test_create_user(api_client):
    """测试创建用户"""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123"
    }
    response = api_client.post("/api/users", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
```

## 最佳实践

1. **使用上下文管理器**: 确保客户端正确关闭
2. **使用响应模型**: 利用 Pydantic 进行数据验证和类型安全
3. **合理设置超时**: 根据接口响应时间设置合适的超时时间
4. **错误处理**: 使用自定义异常类进行精确的错误处理
5. **重试机制**: 对于不稳定的网络环境，设置合理的重试次数
6. **日志记录**: 客户端会自动记录请求和响应信息，便于调试

