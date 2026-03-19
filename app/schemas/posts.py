from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PostCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    is_published: bool = False


class PostUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    is_published: bool


class PostPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    is_published: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data):
        # We must allow omitted fields, but reject explicit JSON `null` values.
        if not isinstance(data, dict):
            return data

        if "title" in data and data["title"] is None:
            raise ValueError("`title` must be a non-empty string (null is not allowed).")
        if "content" in data and data["content"] is None:
            raise ValueError("`content` must be a non-empty string (null is not allowed).")
        if "is_published" in data and data["is_published"] is None:
            raise ValueError("`is_published` must be a boolean (null is not allowed).")

        return data


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    is_published: bool
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    limit: int
    offset: int

