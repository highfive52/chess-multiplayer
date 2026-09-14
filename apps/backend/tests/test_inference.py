import chess
import numpy as np
from moves import encode_move
from services import inference as inference_service


class FakeSession:
    def __init__(self, logits):
        self.logits = logits
        self.last_feed = None

    def run(self, output_names, input_feed):
        self.last_feed = input_feed
        return [self.logits]


def test_onnx_policy_predictor_decodes_best_move(monkeypatch, tmp_path):
    predicted_move_id = encode_move(chess.Move.from_uci("e2e4"))
    logits = np.zeros((1, 20480), dtype=np.float32)
    logits[0, predicted_move_id] = 25.0

    fake_session = FakeSession(logits)
    monkeypatch.setattr(
        inference_service.ort,
        "InferenceSession",
        lambda path: fake_session,
    )

    metadata_path = tmp_path / "policy_v1.json"
    metadata_path.write_text(
        """
        {
          "model_version": "policy-v1",
          "architecture_version": "policy-cnn-v1",
          "board_encoding_version": "board-v1",
          "move_encoding_version": "move-v1",
          "move_class_count": 20480
        }
        """.strip(),
        encoding="utf-8",
    )

    predictor = inference_service.ONNXPolicyPredictor(
        tmp_path / "policy_v1.onnx",
        metadata_path,
    )

    prediction = predictor.predict(chess.STARTING_FEN)

    assert fake_session.last_feed is not None
    assert fake_session.last_feed["board"].shape == (1, 18, 8, 8)
    assert prediction.from_square == "e2"
    assert prediction.to_square == "e4"
    assert prediction.promotion is None
    assert prediction.model_version == "policy-v1"
    assert prediction.score > 0.99


def test_metadata_validation_rejects_incompatible_model(tmp_path):
    metadata_path = tmp_path / "policy_v1.json"
    metadata_path.write_text(
        """
        {
          "model_version": "policy-v2",
          "architecture_version": "policy-cnn-v1",
          "board_encoding_version": "board-v1",
          "move_encoding_version": "move-v1",
          "move_class_count": 20480
        }
        """.strip(),
        encoding="utf-8",
    )

    try:
        inference_service.ONNXPolicyPredictor(
            tmp_path / "policy_v1.onnx",
            metadata_path,
        )
    except RuntimeError as exc:
        assert "Incompatible model artifact metadata" in str(exc)
    else:
        raise AssertionError("Expected incompatible metadata to be rejected")
