from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_posts_service
from app.schemas.posts import (
    PostCreateRequest,
    PostListResponse,
    PostPatchRequest,
    PostResponse,
    PostUpdateRequest,
)
from app.services.posts_service import PostsService

router = APIRouter()


@router.post("/posts", response_model=PostResponse, status_code=201)
def create_post(
    payload: PostCreateRequest,
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return service.create_post(payload)


@router.get("/posts", response_model=PostListResponse)
def list_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PostsService = Depends(get_posts_service),
) -> PostListResponse:
    return service.list_posts(limit=limit, offset=offset)


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: UUID,
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return service.get_post_by_id(post_id)


@router.put("/posts/{post_id}", response_model=PostResponse)
def put_post(
    post_id: UUID,
    payload: PostUpdateRequest,
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return service.put_post(post_id=post_id, payload=payload)


@router.patch("/posts/{post_id}", response_model=PostResponse)
def patch_post(
    post_id: UUID,
    payload: PostPatchRequest,
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return service.patch_post(post_id=post_id, payload=payload)


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: UUID,
    service: PostsService = Depends(get_posts_service),
) -> Response:
    service.delete_post(post_id=post_id)
    return Response(status_code=204)

