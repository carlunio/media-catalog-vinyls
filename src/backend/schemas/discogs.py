from pydantic import BaseModel
from typing import Optional


class DiscogsSearchResult(BaseModel):
    id: int
    title: str
    thumb: Optional[str] = None
