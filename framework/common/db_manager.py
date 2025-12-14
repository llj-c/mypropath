from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from framework.abs.abs_db_manager import ABSDBManager
from framework.config.fw_config import FWConfig


class DBManager(ABSDBManager):
    """数据库管理器具体实现类, 使用 FWConfig 的 database 配置."""

    def __init__(self, config: FWConfig):
        """
        初始化数据库管理器.

        Args:
            config: 框架配置对象, 包含 database 配置
        """
        self.config = config
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def _create_engine(self) -> Engine:
        """
        创建 SQLAlchemy Engine 实例.

        Returns:
            Engine: SQLAlchemy Engine 实例
        """
        mysql_config = self.config.database.mysql
        return create_engine(
            mysql_config.build_connection_url(),
            pool_size=mysql_config.pool_size,
            max_overflow=mysql_config.max_overflow,
            pool_timeout=mysql_config.pool_timeout,
            pool_recycle=mysql_config.pool_recycle,
            pool_pre_ping=mysql_config.pool_pre_ping,
            pool_reset_on_return="rollback",
        )

    def _get_session_factory(self) -> sessionmaker[Session]:
        """
        获取 Session 工厂函数.

        Returns:
            sessionmaker: Session 工厂函数
        """
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
        return self._session_factory

    def get_engine(self) -> Engine:
        """
        获取 SQLAlchemy Engine 实例 (懒加载).

        Returns:
            Engine: SQLAlchemy Engine 实例
        """
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def get_session(self) -> Session:
        """
        获取原始 Session, 由调用方自行管理提交/回滚.

        Returns:
            Session: SQLAlchemy Session 实例
        """
        session_factory = self._get_session_factory()
        return session_factory()

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
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """
        释放连接池资源.
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
