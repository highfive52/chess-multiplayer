from fastapi.testclient import TestClient
from main import app
from services.inference import MovePrediction
from services.ml_player import MLPlayer


class FakePredictor:
    def __init__(self, onnx_path, metadata_path):
        self.onnx_path = onnx_path
        self.metadata_path = metadata_path

    def predict(self, fen: str) -> MovePrediction:
        return MovePrediction(
            from_square="e2",
            to_square="e4",
            promotion=None,
            score=0.75,
            model_version="test-model",
        )


def test_app_lifespan_initializes_ml_player(
    monkeypatch,
):
    monkeypatch.setattr("services.ml_player.ONNXPolicyPredictor", FakePredictor)
    monkeypatch.setenv(
        "ML_MODEL_ONNX_PATH",
        "artifacts/policy_v1.onnx",
    )

    monkeypatch.setenv(
        "ML_MODEL_METADATA_PATH",
        "artifacts/policy_v1.json",
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
