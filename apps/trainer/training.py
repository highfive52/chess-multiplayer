"""Reusable training utilities for the chess policy model."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from dataset import ChessPolicyDataset
from evaluation import EpochMetrics, evaluate
from torch import nn
from torch.utils.data import DataLoader


@dataclass(frozen=True)
class TrainingState:
    """Captured state from one optimization step set."""

    metrics: EpochMetrics


def _top_k_correct(
    logits: torch.Tensor,
    targets: torch.Tensor,
    *,
    k: int,
) -> int:
    top_k_predictions = torch.topk(
        logits,
        k=k,
        dim=1,
    ).indices

    matches = top_k_predictions.eq(targets.unsqueeze(1))

    return int(matches.any(dim=1).sum().item())


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

        total_loss += loss.item() * batch_size
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


def train_and_evaluate(
    model: nn.Module,
    training_loader: DataLoader,
    validation_loader: DataLoader,
    validation_dataset: ChessPolicyDataset,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[EpochMetrics, EpochMetrics]:
    """Run one training epoch and one validation epoch."""

    training_metrics = train_one_epoch(
        model=model,
        dataloader=training_loader,
        optimizer=optimizer,
        criterion=criterion,
        device=device,
    )

    validation_metrics = evaluate(
        model=model,
        dataloader=validation_loader,
        dataset=validation_dataset,
        criterion=criterion,
        device=device,
    )

    return training_metrics, validation_metrics
