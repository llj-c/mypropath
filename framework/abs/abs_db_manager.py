from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class ABSDBManager(ABC):
    """数据库管理器抽象基类, 负责管理 engine 并向外界提供 session."""

    @abstractmethod
    def get_engine(self) -> Engine:
        """
        获取 SQLAlchemy Engine 实例.

        Returns:
            Engine: SQLAlchemy Engine 实例
        """
        pass

    @abstractmethod
    def get_session(self) -> Session:
        """
        获取原始 Session, 由调用方自行管理提交/回滚.

        Returns:
            Session: SQLAlchemy Session 实例
        """
        pass

    @abstractmethod
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        提供自动提交/回滚的会话上下文管理器.

        Yields:
            Session: SQLAlchemy Session 实例

        Example:
            ```python
            with db_manager.session_scope() as session:
                # 使用 session 进行操作
                pass
            ```
        """
        pass

    @abstractmethod
    def dispose(self) -> None:
        """
        释放连接池资源.
        """
        pass