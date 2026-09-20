from fastapi import FastAPI

app = FastAPI(
    title="lv-optimizer",
    description="Genetic Algorithm optimization microservice for the Green-VRP",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
