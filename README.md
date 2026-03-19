# REST API for Redis testing

## Stack
- `FastAPI` + `Pydantic`
- `SQLAlchemy (sync)` + `PostgreSQL` + `Alembic`
- `Redis`
- `pytest` (integration tests)

## How to run

1. Ensure Docker is running.
2. Create `.env` from `.env.example` (if you plan to run outside of Docker defaults).
3. Start the whole stack:

```bash
docker compose up --build
```

API will be available on: `http://localhost:8006`

Health endpoint:
- `GET /health` -> `200 {"status": "ok"}`

## How to run tests

```bash
docker compose run --rm --build test
```

## REST API Contract

### Endpoints

`POST /posts`
- Body: `PostCreateRequest`
- Success: `201` + `PostResponse`

`GET /posts`
- Query: `limit` (1..100, default `20`), `offset` (>=0, default `0`)
- Success: `200` + `PostListResponse`

`GET /posts/{post_id}`
- Success: `200` + `PostResponse`
- Not found: `404` + `{"code":"POST_NOT_FOUND","message":"..." }`

`PUT /posts/{post_id}`
- Body: `PostUpdateRequest` (all fields required)
- Success: `200` + `PostResponse`
- Not found: `404` + `{"code":"POST_NOT_FOUND","message":"..." }`

`PATCH /posts/{post_id}`
- Body: `PostPatchRequest` (partial update; only provided fields are updated)
- Success: `200` + `PostResponse`
- Not found: `404` + `{"code":"POST_NOT_FOUND","message":"..." }`

`DELETE /posts/{post_id}`
- Success: `204` (no body)
- Not found: `404` + `{"code":"POST_NOT_FOUND","message":"..." }`

### Error payloads

`404` (missing post):
```json
{ "code": "POST_NOT_FOUND", "message": "Post with id '<uuid>' not found." }
```

`422` (validation):
- Uses FastAPI/Pydantic validation.
- Validation messages are in English and come from schema validators.
- Example for PATCH with explicit `null`: `title` / `content` / `is_published` reject `null` with a clear English message.

## Models (request/response)

`PostCreateRequest`
- `title: string` (min length 1)
- `content: string` (min length 1)
- `is_published: boolean` (default `false`)

`PostUpdateRequest` (PUT)
- `title: string` (min length 1)
- `content: string` (min length 1)
- `is_published: boolean`

`PostPatchRequest` (PATCH)
- Optional fields: `title`, `content`, `is_published`
- Explicit `null` for any of these fields is rejected with `422`

`PostResponse`
- `id, title, content, is_published, created_at, updated_at`

`PostListResponse`
- `items: PostResponse[]`
- `total: int`, `limit: int`, `offset: int`

## Caching design (cache-aside)

For `GET /posts/{id}` we use **cache-aside** (lazy loading):
1) Build Redis key: `{POST_CACHE_PREFIX}:v1:post:{id}`
2) Try Redis GET.
3) On hit: return cached `PostResponse`.
4) On miss: load from PostgreSQL.
5) Serialize `PostResponse` into JSON and `SET` it in Redis with TTL (`POST_CACHE_TTL_SECONDS`).
6) Return the DB result.

Cold-cache stampede mitigation:
- On miss we acquire a short-lived Redis lock: `{POST_CACHE_PREFIX}:v1:lock:post:{id}` (`SET NX EX`).
- If the lock is already held by another request, we poll Redis for a short time and reuse the value once it appears.

Invalidation policy:
- `PUT /posts/{id}`, `PATCH /posts/{id}`, `DELETE /posts/{id}` invalidate the single-post cache by deleting
  `{POST_CACHE_PREFIX}:v1:post:{id}`.
- Invalidation happens **after** successful PostgreSQL update/delete (so the next GET observes the new state).
- `GET /posts/{id}` when the post does not exist returns `404` and does **not** populate Redis.

Redis failures:
- Cache read/write errors do not break API correctness (we log warnings and fall back to PostgreSQL).

## Environment

See `.env.example` for required variables.

### Notes on reliability

Cold-cache `GET /posts/{id}` anti-stampede:
- we use a short-lived Redis lock (`SET NX EX`) so only one request repopulates Redis on a miss
- other requests poll Redis briefly and then return the cached value

## Quick curl smoke test

Base URL (FastAPI): `http://localhost:8006`

### Bash / curl
```bash
BASE_URL="http://localhost:8006"
```

```bash
POST_PAYLOAD='{"title":"Smoke title","content":"Smoke content","is_published":false}'
```

```bash
POST_RESP="$(curl -s -X POST "$BASE_URL/posts" \
  -H "Content-Type: application/json" \
  -d "$POST_PAYLOAD")"
```

```bash
POST_ID="$(echo "$POST_RESP" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
```

```bash
curl -s -X GET "$BASE_URL/posts/$POST_ID"
```

```bash
PUT_PAYLOAD='{"title":"Updated via PUT","content":"Updated content","is_published":true}'
```

```bash
curl -s -X PUT "$BASE_URL/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d "$PUT_PAYLOAD"
```

```bash
PATCH_PAYLOAD='{"title":"Updated via PATCH"}'
```

```bash
curl -s -X PATCH "$BASE_URL/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d "$PATCH_PAYLOAD"
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE "$BASE_URL/posts/$POST_ID"
```

```bash
curl -s -X GET "$BASE_URL/posts/$POST_ID"
```

### PowerShell / curl.exe
```powershell
$BASE_URL = "http://localhost:8006"
```

```powershell
$postPayload = @{
  title = "Smoke title"
  content = "Smoke content"
  is_published = $false
} | ConvertTo-Json -Compress
```

```powershell
$postResp = curl.exe -s -X POST "$BASE_URL/posts" `
  -H "Content-Type: application/json" `
  -d $postPayload
```

```powershell
$postId = ($postResp | ConvertFrom-Json).id
```

```powershell
curl.exe -s -X GET "$BASE_URL/posts/$postId"
```

```powershell
$putPayload = @{
  title = "Updated via PUT"
  content = "Updated content"
  is_published = $true
} | ConvertTo-Json -Compress
```

```powershell
curl.exe -s -X PUT "$BASE_URL/posts/$postId" `
  -H "Content-Type: application/json" `
  -d $putPayload
```

```powershell
$patchPayload = @{ title = "Updated via PATCH" } | ConvertTo-Json -Compress
```

```powershell
curl.exe -s -X PATCH "$BASE_URL/posts/$postId" `
  -H "Content-Type: application/json" `
  -d $patchPayload
```

```powershell
curl.exe -s -o /dev/null -w "%{http_code}`n" -X DELETE "$BASE_URL/posts/$postId"
```

```powershell
curl.exe -s -X GET "$BASE_URL/posts/$postId"
```
