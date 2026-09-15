"""Model artifact metadata loading and compatibility validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import torch
from moves import MOVE_CLASS_COUNT

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


@dataclass(frozen=True)
class ModelArtifactPaths:
    """Canonical paths for a model's local artifacts."""

    checkpoint_path: Path
    onnx_path: Path
    metadata_path: Path


def find_repo_root(start: str | Path | None = None) -> Path:
    """Locate the repository root by walking upward from a starting path."""

    current = Path(start or __file__).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (
            candidate / "artifacts"
        ).exists():
            return candidate

    raise FileNotFoundError("Could not locate the repository root")


def build_model_artifact_paths(
    start: str | Path | None = None,
    *,
    artifact_stem: str = "policy_v1",
) -> ModelArtifactPaths:
    """Return the canonical artifact paths for a model version."""

    repo_root = find_repo_root(start)
    artifacts_dir = repo_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    return ModelArtifactPaths(
        checkpoint_path=artifacts_dir / f"{artifact_stem}.safetensors",
        onnx_path=artifacts_dir / f"{artifact_stem}.onnx",
        metadata_path=artifacts_dir / f"{artifact_stem}.json",
    )


def build_model_metadata_payload(
    *,
    artifact_stem: str = "policy_v1",
    onnx_opset: int | None = None,
    extra_fields: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the JSON metadata payload for a model artifact."""

    payload: dict[str, object] = {
        "model_version": EXPECTED_MODEL_VERSION,
        "architecture_version": EXPECTED_ARCHITECTURE_VERSION,
        "board_encoding_version": EXPECTED_BOARD_ENCODING_VERSION,
        "move_encoding_version": EXPECTED_MOVE_ENCODING_VERSION,
        "move_class_count": EXPECTED_MOVE_CLASS_COUNT,
        "safetensors_file": f"{artifact_stem}.safetensors",
        "onnx_file": f"{artifact_stem}.onnx",
        "metadata_file": f"{artifact_stem}.json",
    }

    if onnx_opset is not None:
        payload["onnx_opset"] = onnx_opset

    if extra_fields:
        payload.update(extra_fields)

    return payload


def load_model_metadata(
    metadata_path: str | Path,
) -> ModelArtifactMetadata:
    """Load model artifact metadata from JSON."""

    path = Path(metadata_path)

    with path.open("r", encoding="utf-8") as file:
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


def save_safetensors_checkpoint(model, checkpoint_path: str | Path) -> None:
    """Persist a model state dict using Safetensors."""

    try:
        from safetensors.torch import save_file
    except ImportError as exc:  # pragma: no cover - dependency wiring
        raise RuntimeError(
            "safetensors is required to save trainer checkpoints"
        ) from exc

    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(model.state_dict(), str(path))


def load_safetensors_checkpoint(model, checkpoint_path: str | Path) -> None:
    """Load a Safetensors checkpoint into a model instance."""

    try:
        from safetensors.torch import load_file
    except ImportError as exc:  # pragma: no cover - dependency wiring
        raise RuntimeError(
            "safetensors is required to load trainer checkpoints"
        ) from exc

    state_dict = load_file(str(checkpoint_path))
    model.load_state_dict(state_dict)


def write_model_metadata(
    metadata_path: str | Path,
    payload: Mapping[str, object],
) -> None:
    """Write model metadata to JSON with stable formatting."""

    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


def export_onnx_model(
    model,
    onnx_path: str | Path,
    *,
    opset_version: int = 18,
) -> None:
    """Export a PolicyCNN-style model to ONNX."""

    try:
        import onnx  # noqa: F401
    except ImportError as exc:  # pragma: no cover - dependency wiring
        raise RuntimeError("onnx is required to export trainer models") from exc

    path = Path(onnx_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    device = next(model.parameters()).device
    dummy_input = torch.zeros(
        (1, 18, 8, 8),
        dtype=torch.float32,
        device=device,
    )

    model.eval()
    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_input,
            str(path),
            export_params=True,
            opset_version=opset_version,
            external_data=False,
            do_constant_folding=True,
            input_names=["board"],
            output_names=["logits"],
            dynamic_axes={
                "board": {0: "batch"},
                "logits": {0: "batch"},
            },
        )


def publish_model_artifacts(
    artifact_paths: ModelArtifactPaths,
    *,
    repo_id: str,
    token: str | None = None,
) -> None:
    """Publish model artifacts to a Hugging Face model repository."""

    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required to publish model artifacts"
        ) from exc

    paths = (
        artifact_paths.checkpoint_path,
        artifact_paths.onnx_path,
        artifact_paths.metadata_path,
    )

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Model artifact does not exist: {path}")

    api = HfApi(token=token)

    api.create_repo(
        repo_id=repo_id,
        repo_type="model",
        private=True,
        exist_ok=True,
    )

    for path in paths:
        api.upload_file(
            path_or_fileobj=path,
            path_in_repo=path.name,
            repo_id=repo_id,
            repo_type="model",
        )
