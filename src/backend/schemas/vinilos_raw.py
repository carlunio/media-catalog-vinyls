from pydantic import BaseModel
from typing import Dict, Any


class ViniloRawIn(BaseModel):
    id: str
    data: Dict[str, Any]
    overwrite: bool = False
