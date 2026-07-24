from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from api.app import rank, upload
from api.app.db.session import engine

app = FastAPI()
app.include_router(upload.router)
app.include_router(rank.router)


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"database unreachable: {e}") from e
    return {"status": "ok"}
