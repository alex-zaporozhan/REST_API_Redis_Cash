import time
from uuid import UUID

from app.cache.post_cache import PostCache
from app.repositories.posts_repository import PostsRepository
from app.schemas.posts import (
    PostCreateRequest,
    PostListResponse,
    PostPatchRequest,
    PostResponse,
    PostUpdateRequest,
)


class PostNotFoundError(Exception):
    pass


class PostsService:
    def __init__(self, repo: PostsRepository, cache: PostCache):
        self._repo = repo
        self._cache = cache

    def create_post(self, payload: PostCreateRequest) -> PostResponse:
        post = self._repo.create(payload)
        return PostResponse.model_validate(post)

    def get_post_by_id(self, post_id: UUID) -> PostResponse:
        cached = self._cache.get_by_id(post_id)
        if cached is not None:
            return cached

        # Anti-stampede: only one request should repopulate the cache on a cold miss.
        # Others will wait briefly for Redis to be filled.
        token = self._cache.acquire_post_lock(post_id)
        try:
            if token is None:
                # Another worker likely repopulates the cache. Poll Redis a bit.
                for _ in range(25):
                    cached_retry = self._cache.get_by_id(post_id)
                    if cached_retry is not None:
                        return cached_retry
                    time.sleep(0.02)

            post = self._repo.get_by_id(post_id)
            if post is None:
                # Ensure we don't create a cache entry for missing posts.
                raise PostNotFoundError(f"Post with id '{post_id}' not found.")

            response = PostResponse.model_validate(post)
            self._cache.set_by_id(response)
            return response
        finally:
            if token is not None:
                self._cache.release_post_lock(post_id, token=token)

    def put_post(self, post_id: UUID, payload: PostUpdateRequest) -> PostResponse:
        post = self._repo.update_put(post_id, payload)
        if post is None:
            raise PostNotFoundError(f"Post with id '{post_id}' not found.")

        response = PostResponse.model_validate(post)
        # Invalidate after DB write, so next GET sees the updated version.
        self._cache.delete_by_id(post_id)
        return response

    def patch_post(self, post_id: UUID, payload: PostPatchRequest) -> PostResponse:
        post = self._repo.update_patch(post_id, payload)
        if post is None:
            raise PostNotFoundError(f"Post with id '{post_id}' not found.")

        response = PostResponse.model_validate(post)
        self._cache.delete_by_id(post_id)
        return response

    def delete_post(self, post_id: UUID) -> None:
        deleted = self._repo.delete(post_id)
        if not deleted:
            raise PostNotFoundError(f"Post with id '{post_id}' not found.")

        self._cache.delete_by_id(post_id)

    def list_posts(self, *, limit: int, offset: int) -> PostListResponse:
        posts, total = self._repo.list_posts(limit=limit, offset=offset)
        items = [PostResponse.model_validate(p) for p in posts]
        return PostListResponse(items=items, total=total, limit=limit, offset=offset)

