import math

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


def test_onnx_policy_predictor_ignores_illegal_global_top_class(
    monkeypatch,
    tmp_path,
):
    legal_move_id = encode_move(chess.Move.from_uci("d2d4"))
    illegal_move_id = encode_move(chess.Move.from_uci("e7e5"))

    logits = np.zeros((1, 20480), dtype=np.float32)
    logits[0, legal_move_id] = 5.0
    logits[0, illegal_move_id] = 25.0

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

    assert prediction.from_square == "d2"
    assert prediction.to_square == "d4"
    assert prediction.promotion is None
    assert prediction.model_version == "policy-v1"


def test_onnx_policy_predictor_scores_legal_moves_only(monkeypatch, tmp_path):
    board = chess.Board(chess.STARTING_FEN)
    d2d4_move_id = encode_move(chess.Move.from_uci("d2d4"))
    e2e4_move_id = encode_move(chess.Move.from_uci("e2e4"))
    illegal_move_id = encode_move(chess.Move.from_uci("e7e5"))

    logits = np.zeros((1, 20480), dtype=np.float32)
    for move in board.legal_moves:
        logits[0, encode_move(move)] = -1000.0

    logits[0, d2d4_move_id] = 3.0
    logits[0, e2e4_move_id] = 2.0
    logits[0, illegal_move_id] = 10.0

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

    expected_score = math.exp(3.0) / (math.exp(3.0) + math.exp(2.0))

    assert prediction.from_square == "d2"
    assert prediction.to_square == "d4"
    assert prediction.promotion is None
    assert prediction.model_version == "policy-v1"
    assert math.isclose(prediction.score, expected_score, rel_tol=1e-6)


def test_onnx_policy_predictor_handles_promotion_moves(monkeypatch, tmp_path):
    promotion_move_id = encode_move(chess.Move.from_uci("e7e8q"))
    logits = np.zeros((1, 20480), dtype=np.float32)
    logits[0, promotion_move_id] = 12.0

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

    prediction = predictor.predict("6k1/4P3/8/8/8/8/8/4K3 w - - 0 1")

    assert prediction.from_square == "e7"
    assert prediction.to_square == "e8"
    assert prediction.promotion == "queen"


def test_onnx_policy_predictor_rejects_no_legal_moves(monkeypatch, tmp_path):
    fake_session = FakeSession(np.zeros((1, 20480), dtype=np.float32))
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

    try:
        predictor.predict("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1")
    except RuntimeError as exc:
        assert "No legal moves available for position" in str(exc)
    else:
        raise AssertionError("Expected positions without legal moves to fail")


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
