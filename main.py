

from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from framework.common.db_manager import DBManager
from framework.config import FWConfig
from framework.containers.app_container import AppContainer
from framework.frame_logger import frame_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理, 负责依赖注入容器的初始化和资源清理."""
    container = AppContainer()
    container.wire(modules=[__name__])
    yield
    # 应用关闭时清理数据库资源
    db_manager: DBManager = container.db_manager()
    db_manager.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def index():
    frame_logger.info("get index success")
    return {
        "hello world"
    }


@app.get("/db-test")
@inject
def db_test(db_manager: DBManager = Provide[AppContainer.db_manager]):
    """
    数据库连接测试示例.

    展示如何在 FastAPI 路由中使用依赖注入的 DBManager.
    """
    with db_manager.session_scope() as session:
        # 使用 session 进行数据库操作
        # 例如: result = session.execute(text("SELECT 1"))
        return {"status": "success", "message": "数据库连接正常"}


@inject
def main(config: FWConfig = Provide["config"]):
    uvicorn.run(app, host=config.app_host, port=config.app_port)


if __name__ == "__main__":
    container = AppContainer()
    container.wire(modules=[__name__])
    main()