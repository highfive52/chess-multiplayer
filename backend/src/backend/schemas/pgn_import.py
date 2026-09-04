from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ImportedMove(BaseModel):
    ply: int
    san: str
    fen_after: str
    from_square: Optional[str] = None
    to_square: Optional[str] = None
    promotion: Optional[str] = None


class ParsedPgnGame(BaseModel):
    metadata: Dict[str, Any] = {}
    initial_fen: Optional[str] = None
    moves: List[ImportedMove] = []
    warnings: List[str] = []


class ImportDiagnostic(BaseModel):
    code: str
    message: str
    game_index: Optional[int] = None
    ply: Optional[int] = None


class ImportedGameResult(BaseModel):
    game_index: int
    game_id: Optional[str] = None
    move_count: int
    warnings: List[str] = []


class ImportResponse(BaseModel):
    imported: List[ImportedGameResult] = []
    failed: List[ImportDiagnostic] = []
