"""traceid管理模块 - 用于测试用例的跟踪ID管理"""

import contextvars
import uuid
from typing import Optional

# 使用contextvars确保traceid在异步环境中正确传递
traceid_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "traceid", default=None
)


def generate_traceid() -> str:
    """生成唯一的traceid"""
    return str(uuid.uuid4())


def set_traceid(traceid: str) -> None:
    """设置当前上下文的traceid"""
    traceid_context.set(traceid)


def get_traceid() -> str:
    """获取当前测试用例的traceid，如果不存在则返回unknown"""
    traceid = traceid_context.get()
    return traceid if traceid else "unknown"


def clear_traceid() -> None:
    """清除当前上下文的traceid"""
    traceid_context.set(None)

