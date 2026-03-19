import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.posts import router as posts_router
from app.services.posts_service import PostNotFoundError


app = FastAPI(title="Posts API with Redis caching", version="1.0")
app.include_router(posts_router)

logger = logging.getLogger(__name__)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(PostNotFoundError)
def handle_post_not_found(_, exc: PostNotFoundError) -> JSONResponse:
    logger.warning("Request failed: %s", exc)
    return JSONResponse(
        status_code=404,
        content={"code": "POST_NOT_FOUND", "message": str(exc) or "Post not found."},
    )

