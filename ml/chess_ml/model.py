"""Convolutional policy model for chess move prediction."""

from __future__ import annotations

import torch
from torch import nn

from chess_ml.moves import MOVE_CLASS_COUNT

    # 1. Human/domain representation
    #
    # chess.Board
    # "White knight is on g1"
    # "White can castle kingside"
    # "Black to move"
    #         ↓
    #
    # 2. Machine input representation
    #
    # 18 × 8 × 8
    # hand-designed features
    #         ↓
    #
    # 3. Learned representation
    #
    # spatial feature maps
    #
    # 32 × 8 × 8
    #       ↓
    # 64 × 8 × 8
    #       ↓
    # 64 × 8 × 8
    #       ↓
    # flatten
    #       ↓
    # 4096 features
    #       ↓
    # dense representation
    #
    # 256 features
    #
    # 4. Prediction representation
    #
    # 20,480 logits
    #       ↓
    # move class
    #       ↓
    # chess.Move
    #
    
    #------

    #              width
    #               ↑
    # 18 → 32 → 64 → 64
    #       └───────────
    #           depth →

class PolicyCNN(nn.Module):
    """Small convolutional network for chess move classification."""

    def __init__(self) -> None:
        super().__init__()

        # Spacial extraction through convolutional layers
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

        # Move classification through fully connected layers
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

# input
# [N, 18, 8, 8]

#     ↓

# Conv2d
# [N, 32, 8, 8]

#     ↓

# Conv2d
# [N, 64, 8, 8]

#     ↓

# Conv2d
# [N, 64, 8, 8]

#     ↓

# Flatten
# [N, 4096]

#     ↓

# Linear
# [N, 256]

#     ↓

# Linear
# [N, 20_480]