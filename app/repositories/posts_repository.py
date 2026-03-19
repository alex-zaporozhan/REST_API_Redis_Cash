from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Post
from app.schemas.posts import (
    PostCreateRequest,
    PostPatchRequest,
    PostResponse,
    PostUpdateRequest,
)


class PostsRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, payload: PostCreateRequest) -> Post:
        post = Post(
            title=payload.title,
            content=payload.content,
            is_published=payload.is_published,
        )
        self._session.add(post)
        self._session.commit()
        self._session.refresh(post)
        return post

    def get_by_id(self, post_id: UUID) -> Post | None:
        return self._session.get(Post, post_id)

    def update_put(self, post_id: UUID, payload: PostUpdateRequest) -> Post | None:
        post = self.get_by_id(post_id)
        if post is None:
            return None

        post.title = payload.title
        post.content = payload.content
        post.is_published = payload.is_published
        post.touch()

        self._session.add(post)
        self._session.commit()
        self._session.refresh(post)
        return post

    def update_patch(self, post_id: UUID, payload: PostPatchRequest) -> Post | None:
        post = self.get_by_id(post_id)
        if post is None:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        for key, value in patch_data.items():
            setattr(post, key, value)

        post.touch()
        self._session.add(post)
        self._session.commit()
        self._session.refresh(post)
        return post

    def delete(self, post_id: UUID) -> bool:
        post = self.get_by_id(post_id)
        if post is None:
            return False

        self._session.delete(post)
        self._session.commit()
        return True

    def list_posts(self, *, limit: int, offset: int) -> tuple[list[Post], int]:
        total = self._session.execute(select(func.count()).select_from(Post)).scalar_one()

        items = (
            self._session.execute(
                select(Post)
                .order_by(Post.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return items, total

