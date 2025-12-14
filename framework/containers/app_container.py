from dependency_injector import containers, providers

from framework.common.db_manager import DBManager
from framework.config import FWConfig


class AppContainer(containers.DeclarativeContainer):
    """应用依赖注入容器."""

    config = providers.Factory(FWConfig)

    db_manager = providers.Singleton(
        DBManager,
        config=config,
    )
