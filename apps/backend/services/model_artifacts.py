"""Model artifact acquisition for backend inference."""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import hf_hub_download


def ensure_model_artifacts() -> None:
    """Ensure model artifacts required for inference exist locally."""

    repo_id = os.getenv("HF_MODEL_REPO_ID")
    token = os.getenv("HF_TOKEN")

    onnx_path = Path(
        os.getenv(
            "ML_MODEL_ONNX_PATH",
            "artifacts/policy_v1.onnx",
        )
    )
    metadata_path = Path(
        os.getenv(
            "ML_MODEL_METADATA_PATH",
            "artifacts/policy_v1.json",
        )
    )

    if onnx_path.exists() and metadata_path.exists():
        return

    if not repo_id:
        raise RuntimeError("HF_MODEL_REPO_ID is required")

    if not token:
        raise RuntimeError("HF_TOKEN is required")

    onnx_path.parent.mkdir(parents=True, exist_ok=True)

    if not onnx_path.exists():
        hf_hub_download(
            repo_id=repo_id,
            filename=onnx_path.name,
            token=token,
            local_dir=onnx_path.parent,
        )

    if not metadata_path.exists():
        hf_hub_download(
            repo_id=repo_id,
            filename=metadata_path.name,
            token=token,
            local_dir=metadata_path.parent,
        )
