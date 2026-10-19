import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.optimize import router as optimize_router
from app.optimization import process_pool


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await asyncio.get_running_loop().run_in_executor(None, process_pool.warm_up)
    yield
    process_pool.reset_pool()


app = FastAPI(
    title="lv-optimizer",
    description="Genetic Algorithm optimization microservice for the Green-VRP",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(optimize_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
