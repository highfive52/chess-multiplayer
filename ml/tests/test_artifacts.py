"""Tests for model artifact metadata compatibility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chess_ml.artifacts import (
    ModelArtifactMetadata,
    load_model_metadata,
    validate_model_metadata,
)


def test_policy_v1_metadata_is_compatible() -> None:
    metadata_path = (
        Path(__file__).parents[1]
        / "artifacts"
        / "policy_v1.json"
    )

    metadata = load_model_metadata(
        metadata_path
    )

    validate_model_metadata(metadata)

    assert metadata.model_version == "policy-v1"


def test_incompatible_metadata_is_rejected() -> None:
    metadata = ModelArtifactMetadata(
        model_version="policy-v1",
        architecture_version="policy-cnn-v1",
        board_encoding_version="board-v2",
        move_encoding_version="move-v1",
        move_class_count=20_480,
    )

    with pytest.raises(
        RuntimeError,
        match="board_encoding_version",
    ):
        validate_model_metadata(metadata)


def test_missing_required_metadata_is_rejected(
    tmp_path: Path,
) -> None:
    metadata_path = (
        tmp_path
        / "metadata.json"
    )

    metadata_path.write_text(
        json.dumps(
            {
                "model_version": "policy-v1",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        load_model_metadata(metadata_path)