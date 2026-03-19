import pytest
from fastapi.testclient import TestClient

from app.cache.keys import post_cache_key
from app.cache.redis_client import get_redis_client
from app.main import app


@pytest.fixture(scope="session")
def redis_client():
    client = get_redis_client()
    client.flushdb()
    return client


@pytest.fixture
def http_client():
    return TestClient(app)

