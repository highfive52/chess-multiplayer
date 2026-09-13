from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ImportedMove(BaseModel):
    ply: int
    san: str
    fen_after: str
    from_square: str | None = None
    to_square: str | None = None
    promotion: str | None = None


class ParsedPgnGame(BaseModel):
    metadata: dict[str, Any] = {}
    initial_fen: str | None = None
    moves: list[ImportedMove] = []
    warnings: list[str] = []


class ImportDiagnostic(BaseModel):
    code: str
    message: str
    game_index: int | None = None
    ply: int | None = None


class ImportedGameResult(BaseModel):
    game_index: int
    game_id: str | None = None
    move_count: int
    warnings: list[str] = []


class ImportResponse(BaseModel):
    imported: list[ImportedGameResult] = []
    failed: list[ImportDiagnostic] = []
