from fastapi import FastAPI

from app.api.optimize import router as optimize_router

app = FastAPI(
    title="lv-optimizer",
    description="Genetic Algorithm optimization microservice for the Green-VRP",
    version="0.1.0",
)

app.include_router(optimize_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
