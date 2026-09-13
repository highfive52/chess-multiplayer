from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReplayMove(BaseModel):
    ply: int
    san: str
    fen_after: str
    from_square: str | None
    to_square: str | None
    promotion: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReplayDocument(BaseModel):
    game_id: UUID
    room_code: str | None = None
    source_type: str | None = None
    initial_fen: str | None = None
    final_fen: str | None = None
    status: str | None = None
    result: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    moves: list[ReplayMove] = []

    model_config = ConfigDict(from_attributes=True)
