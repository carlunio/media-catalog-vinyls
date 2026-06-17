from pydantic import BaseModel, Field
from typing import Optional


class DiscogsSearchResult(BaseModel):
    id: int
    title: str
    thumb: Optional[str] = None
    labels: list[str] = Field(default_factory=list)
