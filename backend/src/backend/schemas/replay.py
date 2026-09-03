from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class ReplayMove(BaseModel):
    ply: int
    san: str
    fen_after: str
    from_square: Optional[str]
    to_square: Optional[str]
    promotion: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class ReplayDocument(BaseModel):
    game_id: UUID
    room_code: str
    source_type: Optional[str] = None
    initial_fen: Optional[str] = None
    final_fen: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    moves: List[ReplayMove] = []

    class Config:
        orm_mode = True
