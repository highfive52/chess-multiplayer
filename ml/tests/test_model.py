"""Tests for the V1 chess policy CNN."""

import pytest
import torch
from chess_ml.model import PolicyCNN
from chess_ml.moves import MOVE_CLASS_COUNT
from torch import nn


def test_policy_cnn_accepts_single_board_batch():
    model = PolicyCNN()

    x = torch.zeros(
        (1, 18, 8, 8),
        dtype=torch.float32,
    )

    logits = model(x)

    assert logits.shape == (
        1,
        MOVE_CLASS_COUNT,
    )


def test_policy_cnn_accepts_multi_board_batch():
    model = PolicyCNN()

    x = torch.zeros(
        (4, 18, 8, 8),
        dtype=torch.float32,
    )

    logits = model(x)

    assert logits.shape == (
        4,
        MOVE_CLASS_COUNT,
    )


def test_policy_cnn_returns_float_logits():
    model = PolicyCNN()

    x = torch.zeros(
        (2, 18, 8, 8),
        dtype=torch.float32,
    )

    logits = model(x)

    assert logits.dtype == torch.float32


def test_policy_cnn_output_dimension_matches_move_encoder():
    model = PolicyCNN()

    x = torch.zeros(
        (1, 18, 8, 8),
        dtype=torch.float32,
    )

    logits = model(x)

    assert logits.shape[1] == MOVE_CLASS_COUNT


def test_policy_cnn_cross_entropy_loss_is_compatible():
    model = PolicyCNN()

    x = torch.zeros(
        (4, 18, 8, 8),
        dtype=torch.float32,
    )

    y = torch.tensor(
        [0, 405, 1000, MOVE_CLASS_COUNT - 1],
        dtype=torch.long,
    )

    logits = model(x)

    criterion = nn.CrossEntropyLoss()

    loss = criterion(
        logits,
        y,
    )

    assert loss.ndim == 0
    assert torch.isfinite(loss)


def test_policy_cnn_backward_produces_gradients():
    model = PolicyCNN()

    x = torch.randn(
        (4, 18, 8, 8),
        dtype=torch.float32,
    )

    y = torch.tensor(
        [0, 405, 1000, MOVE_CLASS_COUNT - 1],
        dtype=torch.long,
    )

    logits = model(x)

    loss = nn.CrossEntropyLoss()(
        logits,
        y,
    )

    loss.backward()

    parameters_with_gradients = [
        parameter
        for parameter in model.parameters()
        if parameter.requires_grad and parameter.grad is not None
    ]

    assert parameters_with_gradients


def test_all_trainable_parameters_receive_gradients():
    model = PolicyCNN()

    x = torch.randn(
        (4, 18, 8, 8),
        dtype=torch.float32,
    )

    y = torch.tensor(
        [0, 405, 1000, MOVE_CLASS_COUNT - 1],
        dtype=torch.long,
    )

    logits = model(x)

    loss = nn.CrossEntropyLoss()(
        logits,
        y,
    )

    loss.backward()

    for parameter in model.parameters():
        if parameter.requires_grad:
            assert parameter.grad is not None


def test_policy_cnn_does_not_apply_softmax():
    model = PolicyCNN()

    x = torch.randn(
        (2, 18, 8, 8),
        dtype=torch.float32,
    )

    logits = model(x)

    row_sums = logits.sum(dim=1)

    assert not torch.allclose(
        row_sums,
        torch.ones_like(row_sums),
    )


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is not available",
)
def test_policy_cnn_runs_on_cuda():
    device = torch.device("cuda")

    model = PolicyCNN().to(device)

    x = torch.zeros(
        (2, 18, 8, 8),
        dtype=torch.float32,
        device=device,
    )

    logits = model(x)

    assert logits.device.type == "cuda"
    assert logits.shape == (
        2,
        MOVE_CLASS_COUNT,
    )
