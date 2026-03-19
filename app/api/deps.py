from fastapi import Depends

from app.cache.post_cache import PostCache
from app.cache.redis_client import get_redis_client
from app.core.config import settings
from app.db.session import get_session
from app.repositories.posts_repository import PostsRepository
from app.services.posts_service import PostsService


def get_db():
    yield from get_session()


def get_posts_repository(db=Depends(get_db)) -> PostsRepository:
    return PostsRepository(db)


def get_posts_cache():
    redis_client = get_redis_client()
    return PostCache(redis_client=redis_client, ttl_seconds=settings.POST_CACHE_TTL_SECONDS)


def get_posts_service(
    posts_repository=Depends(get_posts_repository),
    posts_cache=Depends(get_posts_cache),
) -> PostsService:
    return PostsService(repo=posts_repository, cache=posts_cache)

