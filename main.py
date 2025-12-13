

from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from framework.config import FWConfig
from framework.containers.app_container import AppContainer

@asynccontextmanager
async def lifespan(app: FastAPI):
    container = AppContainer()
    container.wire(modules=[__name__])
    yield


app = FastAPI()


@app.get("/")
def index():
    return {
        "hello world"
    }


@inject
def main(config: FWConfig = Provide["config"]):
    uvicorn.run(app, host=config.app_host, port=config.app_port)


if __name__ == "__main__":
    container = AppContainer()
    container.wire(modules=[__name__])
    main()