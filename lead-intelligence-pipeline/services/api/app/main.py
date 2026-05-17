from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Lead Intelligence Pipeline", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(router)
