"""Reusable training and evaluation utilities for the chess policy model."""

from __future__ import annotations

from dataclasses import dataclass

import chess
import torch
from torch import nn
from torch.utils.data import DataLoader

from chess_ml.dataset import ChessPolicyDataset
from chess_ml.moves import decode_move


@dataclass(frozen=True)
class EpochMetrics:
    """Metrics collected across one training or validation epoch."""

    loss: float
    top1_accuracy: float
    top3_accuracy: float
    top5_accuracy: float
    illegal_top1_rate: float


def _top_k_correct(
    logits: torch.Tensor,
    targets: torch.Tensor,
    *,
    k: int,
) -> int:
    """Count targets appearing within the top-k predicted classes."""

    top_k_predictions = torch.topk(
        logits,
        k=k,
        dim=1,
    ).indices

    matches = top_k_predictions.eq(
        targets.unsqueeze(1)
    )

    return int(
        matches.any(dim=1).sum().item()
    )


def _count_illegal_top1_predictions(
    logits: torch.Tensor,
    boards: list[chess.Board],
) -> int:
    """Count top-1 predictions that are illegal for their board."""

    predicted_ids = logits.argmax(dim=1)

    illegal_count = 0

    for move_id, board in zip(
        predicted_ids.tolist(),
        boards,
    ):
        predicted_move = decode_move(move_id)

        if predicted_move not in board.legal_moves:
            illegal_count += 1

    return illegal_count


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> EpochMetrics:
    """Train the policy model for one epoch."""

    model.train()

    total_loss = 0.0
    total_examples = 0

    top1_correct = 0
    top3_correct = 0
    top5_correct = 0

    for x, y in dataloader:
        x = x.to(device)
        y = y.to(device)

        optimizer.zero_grad()

        logits = model(x)

        loss = criterion(
            logits,
            y,
        )

        loss.backward()
        optimizer.step()

        batch_size = y.shape[0]

        total_loss += (
            loss.item() * batch_size
        )
        total_examples += batch_size

        top1_correct += _top_k_correct(
            logits,
            y,
            k=1,
        )

        top3_correct += _top_k_correct(
            logits,
            y,
            k=3,
        )

        top5_correct += _top_k_correct(
            logits,
            y,
            k=5,
        )

    return EpochMetrics(
        loss=total_loss / total_examples,
        top1_accuracy=top1_correct / total_examples,
        top3_accuracy=top3_correct / total_examples,
        top5_accuracy=top5_correct / total_examples,
        illegal_top1_rate=float("nan"),
    )


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    dataset: ChessPolicyDataset,
    criterion: nn.Module,
    device: torch.device,
) -> EpochMetrics:
    """Evaluate the policy model on a validation dataset."""

    model.eval()

    total_loss = 0.0
    total_examples = 0

    top1_correct = 0
    top3_correct = 0
    top5_correct = 0

    illegal_top1_count = 0

    example_offset = 0

    with torch.no_grad():
        for x, y in dataloader:
            x = x.to(device)
            y = y.to(device)

            logits = model(x)

            loss = criterion(
                logits,
                y,
            )

            batch_size = y.shape[0]

            total_loss += (
                loss.item() * batch_size
            )
            total_examples += batch_size

            top1_correct += _top_k_correct(
                logits,
                y,
                k=1,
            )

            top3_correct += _top_k_correct(
                logits,
                y,
                k=3,
            )

            top5_correct += _top_k_correct(
                logits,
                y,
                k=5,
            )

            batch_examples = dataset.examples[
                example_offset:
                example_offset + batch_size
            ]

            boards = [
                example.board
                for example in batch_examples
            ]

            illegal_top1_count += (
                _count_illegal_top1_predictions(
                    logits,
                    boards,
                )
            )

            example_offset += batch_size

    return EpochMetrics(
        loss=total_loss / total_examples,
        top1_accuracy=top1_correct / total_examples,
        top3_accuracy=top3_correct / total_examples,
        top5_accuracy=top5_correct / total_examples,
        illegal_top1_rate=(
            illegal_top1_count
            / total_examples
        ),
    )