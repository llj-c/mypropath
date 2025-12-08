from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from framework.config import DatabaseConfig


class DatabaseSessionManager:
    """管理 SQLAlchemy 会话生命周期的工具类."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Engine = self._create_engine()
        self._session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def _create_engine(self) -> Engine:
        """创建底层 Engine."""
        return create_engine(
            self.config.build_connection_url(),
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=self.config.pool_pre_ping,
            echo=self.config.echo,
            pool_reset_on_return="rollback",
            future=True,
        )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """提供自动提交/回滚的会话上下文."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """获取原始 Session, 由调用方自行管理提交/回滚."""
        return self._session_factory()

    def dispose(self) -> None:
        """释放连接池资源."""
        self.engine.dispose()
