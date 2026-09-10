from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ml_player import MLPlayer


def test_app_lifespan_initializes_ml_player(
    monkeypatch,
):
    monkeypatch.setenv(
        "ML_MODEL_PATH",
        "../ml/artifacts/policy_v1.pt",
    )

    monkeypatch.setenv(
        "ML_MODEL_METADATA_PATH",
        "../ml/artifacts/policy_v1.json",
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
