"""Tests for model artifact metadata compatibility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from model_artifacts import (
    ModelArtifactMetadata,
    build_model_artifact_paths,
    build_model_metadata_payload,
    export_onnx_model,
    load_model_metadata,
    load_safetensors_checkpoint,
    save_safetensors_checkpoint,
    write_model_metadata,
    validate_model_metadata,
)
from torch import nn


def test_policy_v1_metadata_is_compatible(tmp_path: Path) -> None:
    metadata_path = tmp_path / "policy_v1.json"

    write_model_metadata(
        metadata_path,
        build_model_metadata_payload(),
    )

    metadata = load_model_metadata(metadata_path)

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
    metadata_path = tmp_path / "metadata.json"

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


def test_model_artifact_paths_are_repo_root_relative(tmp_path: Path) -> None:
    repo_root = tmp_path

    (repo_root / "pyproject.toml").write_text("[project]\nname = 'chess-ml'\n")
    (repo_root / "artifacts").mkdir()

    artifact_paths = build_model_artifact_paths(repo_root)

    assert (
        artifact_paths.checkpoint_path
        == repo_root / "artifacts" / "policy_v1.safetensors"
    )
    assert artifact_paths.onnx_path == repo_root / "artifacts" / "policy_v1.onnx"
    assert artifact_paths.metadata_path == repo_root / "artifacts" / "policy_v1.json"


def test_safetensors_checkpoint_round_trip(tmp_path: Path) -> None:
    class TinyModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear = nn.Linear(2, 2)

    model = TinyModel()
    for parameter in model.parameters():
        parameter.data.fill_(1.5)

    checkpoint_path = tmp_path / "policy_v1.safetensors"
    save_safetensors_checkpoint(model, checkpoint_path)

    restored = TinyModel()
    for parameter in restored.parameters():
        parameter.data.zero_()

    load_safetensors_checkpoint(restored, checkpoint_path)

    for original, loaded in zip(
        model.state_dict().values(),
        restored.state_dict().values(),
    ):
        assert torch.allclose(original, loaded)


def test_onnx_export_writes_file(tmp_path: Path) -> None:
    class TinyModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear = nn.Linear(18 * 8 * 8, 2)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.linear(x.flatten(start_dim=1))

    model = TinyModel()
    onnx_path = tmp_path / "policy_v1.onnx"

    export_onnx_model(model, onnx_path)

    assert onnx_path.exists()
    assert onnx_path.stat().st_size > 0
    assert not onnx_path.with_suffix(".onnx.data").exists()
