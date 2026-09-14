from pathlib import Path

from fastapi.testclient import TestClient
from main import app
from services.ml_player import MLPlayer


def test_app_lifespan_initializes_ml_player(
    monkeypatch,
):
    monkeypatch.setenv(
        "ML_MODEL_PATH",
        str(Path(__file__).resolve().parents[3] / "artifacts" / "policy_v1.pt"),
    )

    monkeypatch.setenv(
        "ML_MODEL_METADATA_PATH",
        str(Path(__file__).resolve().parents[3] / "artifacts" / "policy_v1.json"),
    )

    with TestClient(app):
        assert hasattr(
            app.state,
            "ml_player",
        )

        assert isinstance(
            app.state.ml_player,
            MLPlayer,
        )
