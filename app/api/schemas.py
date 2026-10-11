from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SearchRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query не может быть пустым")
        return value


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rubrics: list[str]
    text: str
    created_date: datetime


class SearchResponse(BaseModel):
    items: list[PostOut]
