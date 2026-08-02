from fastapi import FastAPI

from app.api.content import router as content_router

app = FastAPI(
    title="49Days Distribution Engine",
    version="1.0.0",
)

app.include_router(content_router)


@app.get("/")
def root():
    return {
        "message": "49Days Distribution Engine is running 🚀"
    }