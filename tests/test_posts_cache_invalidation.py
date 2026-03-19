import json
from uuid import UUID, uuid4

from app.cache.keys import post_cache_key


def test_404_does_not_create_cache(http_client, redis_client):
    missing_id = uuid4()
    key = post_cache_key(missing_id)

    assert redis_client.exists(key) == 0

    resp = http_client.get(f"/posts/{missing_id}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "POST_NOT_FOUND"

    assert redis_client.exists(key) == 0


def test_get_populates_cache_after_create(http_client, redis_client):
    create_payload = {"title": "t1", "content": "c1", "is_published": False}
    create_resp = http_client.post("/posts", json=create_payload)
    assert create_resp.status_code == 201

    created = create_resp.json()
    post_id = UUID(created["id"])
    key = post_cache_key(post_id)

    # Cache should be created only after GET (cache-aside).
    assert redis_client.exists(key) == 0

    get_resp = http_client.get(f"/posts/{post_id}")
    assert get_resp.status_code == 200
    got = get_resp.json()

    assert redis_client.exists(key) == 1

    raw = redis_client.get(key)
    assert raw is not None
    cached = json.loads(raw)

    assert cached == got


def test_put_invalidates_cache(http_client, redis_client):
    create_payload = {"title": "t1", "content": "c1", "is_published": False}
    post_id = UUID(http_client.post("/posts", json=create_payload).json()["id"])
    key = post_cache_key(post_id)

    http_client.get(f"/posts/{post_id}")  # populate
    assert redis_client.exists(key) == 1

    put_payload = {"title": "t2", "content": "c2", "is_published": True}
    put_resp = http_client.put(f"/posts/{post_id}", json=put_payload)
    assert put_resp.status_code == 200

    # Invalidate should happen synchronously after successful PUT.
    assert redis_client.exists(key) == 0

    get_resp = http_client.get(f"/posts/{post_id}")
    assert get_resp.status_code == 200
    got = get_resp.json()

    assert got["title"] == "t2"
    assert got["content"] == "c2"
    assert got["is_published"] is True
    assert redis_client.exists(key) == 1


def test_patch_invalidates_cache(http_client, redis_client):
    create_payload = {"title": "t1", "content": "c1", "is_published": False}
    post_id = UUID(http_client.post("/posts", json=create_payload).json()["id"])
    key = post_cache_key(post_id)

    http_client.get(f"/posts/{post_id}")  # populate
    assert redis_client.exists(key) == 1

    patch_payload = {"title": "t2"}
    patch_resp = http_client.patch(f"/posts/{post_id}", json=patch_payload)
    assert patch_resp.status_code == 200

    assert redis_client.exists(key) == 0

    get_resp = http_client.get(f"/posts/{post_id}")
    assert get_resp.status_code == 200
    got = get_resp.json()

    assert got["title"] == "t2"
    assert redis_client.exists(key) == 1


def test_delete_invalidates_cache(http_client, redis_client):
    create_payload = {"title": "t1", "content": "c1", "is_published": False}
    post_id = UUID(http_client.post("/posts", json=create_payload).json()["id"])
    key = post_cache_key(post_id)

    http_client.get(f"/posts/{post_id}")  # populate
    assert redis_client.exists(key) == 1

    del_resp = http_client.delete(f"/posts/{post_id}")
    assert del_resp.status_code == 204

    assert redis_client.exists(key) == 0

    get_resp = http_client.get(f"/posts/{post_id}")
    assert get_resp.status_code == 404

    # Cache should not be resurrected for missing posts.
    assert redis_client.exists(key) == 0


def test_mutations_on_missing_post_do_not_create_cache(http_client, redis_client):
    missing_id = uuid4()
    key = post_cache_key(missing_id)

    assert redis_client.exists(key) == 0

    put_resp = http_client.put(
        f"/posts/{missing_id}",
        json={"title": "x", "content": "y", "is_published": False},
    )
    assert put_resp.status_code == 404
    assert redis_client.exists(key) == 0

    patch_resp = http_client.patch(f"/posts/{missing_id}", json={"title": "x"})
    assert patch_resp.status_code == 404
    assert redis_client.exists(key) == 0

    del_resp = http_client.delete(f"/posts/{missing_id}")
    assert del_resp.status_code == 404
    assert redis_client.exists(key) == 0


def test_get_posts_list_returns_created_posts(http_client, redis_client):
    create_payload = {"title": "t1", "content": "c1", "is_published": False}
    create_resp = http_client.post("/posts", json=create_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()

    list_resp = http_client.get("/posts", params={"limit": 10, "offset": 0})
    assert list_resp.status_code == 200
    body = list_resp.json()

    assert body["total"] >= 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert any(item["id"] == created["id"] for item in body["items"])


def test_patch_null_rejected_and_does_not_invalidate_cache(http_client, redis_client):
    create_payload = {"title": "t1", "content": "c1", "is_published": False}
    post_id = UUID(http_client.post("/posts", json=create_payload).json()["id"])
    key = post_cache_key(post_id)

    # Populate cache.
    http_client.get(f"/posts/{post_id}")
    assert redis_client.exists(key) == 1

    patch_resp = http_client.patch(
        f"/posts/{post_id}",
        json={"title": None},
    )
    assert patch_resp.status_code == 422

    # Since validation fails, cache should remain intact.
    assert redis_client.exists(key) == 1

