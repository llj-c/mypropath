from dependency_injector import providers, containers
from framework.config import FWConfig


class FW_Container(containers.DeclarativeContainer):
    fw_config = providers.Singleton(FWConfig)
    
