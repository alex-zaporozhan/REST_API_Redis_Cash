from uuid import UUID

from app.core.config import settings


def post_cache_key(post_id: UUID) -> str:
    return f"{settings.POST_CACHE_PREFIX}:v1:post:{post_id}"


def post_cache_lock_key(post_id: UUID) -> str:
    return f"{settings.POST_CACHE_PREFIX}:v1:lock:post:{post_id}"

