"""状态存储模块 - 用于主进程和pytest子进程之间的状态共享"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "PENDING"  # 等待启动
    RUNNING = "RUNNING"  # 运行中
    PAUSED = "PAUSED"  # 已暂停
    CANCELLED = "CANCELLED"  # 已中止
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"  # 执行失败


class StateStore(ABC):
    """状态存储抽象基类"""

    @abstractmethod
    def set_status(self, run_id: str, status: TaskStatus) -> None:
        """设置任务状态"""
        pass

    @abstractmethod
    def get_status(self, run_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        pass

    @abstractmethod
    def set_flag(self, run_id: str, flag_name: str, value: bool) -> None:
        """设置标志位（paused/cancelled）"""
        pass

    @abstractmethod
    def check_flag(self, run_id: str, flag_name: str) -> bool:
        """检查标志位"""
        pass

    @abstractmethod
    def wait_for_flag(
        self, run_id: str, flag_name: str, timeout: Optional[float] = None
    ) -> bool:
        """等待标志位变化（用于暂停恢复）"""
        pass

    @abstractmethod
    def set_metadata(self, run_id: str, key: str, value: Any) -> None:
        """设置任务元数据"""
        pass

    @abstractmethod
    def get_metadata(self, run_id: str, key: str) -> Optional[Any]:
        """获取任务元数据"""
        pass


class MemoryStateStore(StateStore):
    """基于内存的状态存储实现（用于单机多进程场景）"""

    def __init__(self):
        """初始化内存状态存储"""
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = None  # 可以后续添加文件锁支持

    def set_status(self, run_id: str, status: TaskStatus) -> None:
        """设置任务状态"""
        if run_id not in self._store:
            self._store[run_id] = {}
        self._store[run_id]["status"] = status.value

    def get_status(self, run_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if run_id not in self._store:
            return None
        status_str = self._store[run_id].get("status")
        if status_str:
            try:
                return TaskStatus(status_str)
            except ValueError:
                return None
        return None

    def set_flag(self, run_id: str, flag_name: str, value: bool) -> None:
        """设置标志位"""
        if run_id not in self._store:
            self._store[run_id] = {}
        self._store[run_id][flag_name] = value

    def check_flag(self, run_id: str, flag_name: str) -> bool:
        """检查标志位"""
        if run_id not in self._store:
            return False
        return self._store[run_id].get(flag_name, False)

    def wait_for_flag(
        self, run_id: str, flag_name: str, timeout: Optional[float] = None
    ) -> bool:
        """等待标志位变化"""
        import time

        start_time = time.time()
        check_interval = 0.5  # 轮询间隔（秒）

        while True:
            # 检查标志位是否已清除
            if not self.check_flag(run_id, flag_name):
                return True

            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            time.sleep(check_interval)

    def set_metadata(self, run_id: str, key: str, value: Any) -> None:
        """设置任务元数据"""
        if run_id not in self._store:
            self._store[run_id] = {}
        if "metadata" not in self._store[run_id]:
            self._store[run_id]["metadata"] = {}
        self._store[run_id]["metadata"][key] = value

    def get_metadata(self, run_id: str, key: str) -> Optional[Any]:
        """获取任务元数据"""
        if run_id not in self._store:
            return None
        metadata = self._store[run_id].get("metadata", {})
        return metadata.get(key)

