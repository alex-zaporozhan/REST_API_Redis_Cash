import json
import logging
import uuid
from uuid import UUID

from redis import Redis

from app.cache.keys import post_cache_key, post_cache_lock_key
from app.schemas.posts import PostResponse

logger = logging.getLogger(__name__)


class PostCache:
    def __init__(self, redis_client: Redis, ttl_seconds: int):
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def get_by_id(self, post_id: UUID) -> PostResponse | None:
        key = post_cache_key(post_id)
        try:
            raw = self._redis.get(key)
        except Exception:  # pragma: no cover (depends on external system)
            logger.warning("Redis GET failed, falling back to DB", exc_info=True)
            return None

        if raw is None:
            return None

        try:
            data = json.loads(raw)
            return PostResponse.model_validate(data)
        except Exception:  # pragma: no cover
            logger.warning("Cached payload is corrupted, ignoring", exc_info=True)
            return None

    def set_by_id(self, post: PostResponse) -> None:
        key = post_cache_key(post.id)
        payload = post.model_dump(mode="json")
        raw = json.dumps(payload)

        try:
            self._redis.set(key, raw, ex=self._ttl_seconds)
        except Exception:  # pragma: no cover
            logger.warning("Redis SET failed, ignoring cache write", exc_info=True)

    def delete_by_id(self, post_id: UUID) -> None:
        key = post_cache_key(post_id)
        try:
            self._redis.delete(key)
        except Exception:  # pragma: no cover
            logger.warning("Redis DEL failed, ignoring", exc_info=True)

    def acquire_post_lock(
        self,
        post_id: UUID,
        *,
        ttl_seconds: int = 10,
    ) -> str | None:
        lock_key = post_cache_lock_key(post_id)
        token = uuid.uuid4().hex
        try:
            acquired = self._redis.set(lock_key, token, nx=True, ex=ttl_seconds)
        except Exception:  # pragma: no cover
            logger.warning("Redis lock acquire failed, continuing without lock", exc_info=True)
            return None

        return token if acquired else None

    def release_post_lock(self, post_id: UUID, *, token: str) -> None:
        lock_key = post_cache_lock_key(post_id)
        lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
          return redis.call('del', KEYS[1])
        else
          return 0
        end
        """
        try:
            self._redis.eval(lua, 1, lock_key, token)
        except Exception:  # pragma: no cover
            logger.warning("Redis lock release failed, ignoring", exc_info=True)

