from dependency_injector import containers, providers
from framework.config import FWConfig


class AppContainer(containers.DeclarativeContainer):
    config = providers.Factory(FWConfig)
