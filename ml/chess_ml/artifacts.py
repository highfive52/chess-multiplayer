"""Model artifact metadata loading and compatibility validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from chess_ml.moves import MOVE_CLASS_COUNT

EXPECTED_MODEL_VERSION = "policy-v1"
EXPECTED_ARCHITECTURE_VERSION = "policy-cnn-v1"
EXPECTED_BOARD_ENCODING_VERSION = "board-v1"
EXPECTED_MOVE_ENCODING_VERSION = "move-v1"
EXPECTED_MOVE_CLASS_COUNT = MOVE_CLASS_COUNT


@dataclass(frozen=True)
class ModelArtifactMetadata:
    """Compatibility metadata for a trained policy artifact."""

    model_version: str
    architecture_version: str
    board_encoding_version: str
    move_encoding_version: str
    move_class_count: int


def load_model_metadata(
    metadata_path: str | Path,
) -> ModelArtifactMetadata:
    """Load model artifact metadata from JSON."""

    path = Path(metadata_path)

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return ModelArtifactMetadata(
        model_version=payload["model_version"],
        architecture_version=payload["architecture_version"],
        board_encoding_version=payload["board_encoding_version"],
        move_encoding_version=payload["move_encoding_version"],
        move_class_count=payload["move_class_count"],
    )


def validate_model_metadata(
    metadata: ModelArtifactMetadata,
) -> None:
    """Validate compatibility with the installed chess_ml package."""

    expected = {
        "model_version": EXPECTED_MODEL_VERSION,
        "architecture_version": EXPECTED_ARCHITECTURE_VERSION,
        "board_encoding_version": EXPECTED_BOARD_ENCODING_VERSION,
        "move_encoding_version": EXPECTED_MOVE_ENCODING_VERSION,
        "move_class_count": EXPECTED_MOVE_CLASS_COUNT,
    }

    actual = {
        "model_version": metadata.model_version,
        "architecture_version": metadata.architecture_version,
        "board_encoding_version": metadata.board_encoding_version,
        "move_encoding_version": metadata.move_encoding_version,
        "move_class_count": metadata.move_class_count,
    }

    mismatches = {
        key: (
            expected[key],
            actual[key],
        )
        for key in expected
        if expected[key] != actual[key]
    }

    if mismatches:
        details = ", ".join(
            f"{key}: expected {expected_value!r}, got {actual_value!r}"
            for key, (
                expected_value,
                actual_value,
            ) in mismatches.items()
        )

        raise RuntimeError(f"Incompatible model artifact metadata: {details}")
