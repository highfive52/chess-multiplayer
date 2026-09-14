"""Convolutional policy model for chess move prediction."""

from __future__ import annotations

import torch
from moves import MOVE_CLASS_COUNT
from torch import nn


class PolicyCNN(nn.Module):
    """Small convolutional network for chess move classification."""

    def __init__(self) -> None:
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(
                in_channels=18,
                out_channels=32,
                kernel_size=3,
                padding=1,
            ),
            nn.ReLU(),
            nn.Conv2d(
                in_channels=32,
                out_channels=64,
                kernel_size=3,
                padding=1,
            ),
            nn.ReLU(),
            nn.Conv2d(
                in_channels=64,
                out_channels=64,
                kernel_size=3,
                padding=1,
            ),
            nn.ReLU(),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(
                64 * 8 * 8,
                256,
            ),
            nn.ReLU(),
            nn.Linear(
                256,
                MOVE_CLASS_COUNT,
            ),
        )

    def forward(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        """Return raw move-class logits for a batch of boards."""

        x = self.features(x)
        x = self.classifier(x)

        return x
