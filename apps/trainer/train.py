"""Command-line training entrypoint for the chess policy model."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path

import torch
from dataset import (
    ChessPolicyDataset,
    build_training_examples,
    split_game_records,
)
from datasets import load_dataset
from model import PolicyCNN
from model_artifacts import (
    build_model_artifact_paths,
    build_model_metadata_payload,
    export_onnx_model,
    save_safetensors_checkpoint,
    write_model_metadata,
)
from torch import nn
from torch.utils.data import DataLoader
from training import evaluate, train_one_epoch

DATASET_NAME = "Lichess/standard-chess-games"
MIN_ELO = 1800
SAMPLE_SIZE = 10_000
VALIDATION_FRACTION = 0.2
SEED = 42
BATCH_SIZE = 256
LEARNING_RATE = 1e-3
EPOCHS = 10


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the repository root from any path inside the workspace."""

    current = (start or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (
            candidate / "artifacts"
        ).exists():
            return candidate

    raise FileNotFoundError("Could not locate the repository root")


def load_filtered_games(
    *,
    dataset_name: str,
    min_elo: int,
    sample_size: int,
) -> list[Mapping[str, object]]:
    """Load and filter Lichess games for supervised policy training."""

    games = load_dataset(
        dataset_name,
        split="train",
        streaming=True,
    )

    filtered_games = games.filter(
        lambda game: (
            game["WhiteElo"] is not None
            and game["BlackElo"] is not None
            and game["WhiteElo"] >= min_elo
            and game["BlackElo"] >= min_elo
            and game["Result"]
            in {
                "1-0",
                "0-1",
                "1/2-1/2",
            }
        )
    )

    return list(filtered_games.take(sample_size))


def run_training(
    *,
    repo_root: Path,
    dataset_name: str = DATASET_NAME,
    min_elo: int = MIN_ELO,
    sample_size: int = SAMPLE_SIZE,
    validation_fraction: float = VALIDATION_FRACTION,
    seed: int = SEED,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    epochs: int = EPOCHS,
) -> dict[str, object]:
    """Train the policy model and persist the best checkpoint."""

    game_records = load_filtered_games(
        dataset_name=dataset_name,
        min_elo=min_elo,
        sample_size=sample_size,
    )

    training_records, validation_records = split_game_records(
        game_records,
        validation_fraction=validation_fraction,
        seed=seed,
    )

    training_examples = build_training_examples(training_records)
    validation_examples = build_training_examples(validation_records)

    training_dataset = ChessPolicyDataset(training_examples)
    validation_dataset = ChessPolicyDataset(validation_examples)

    training_loader = DataLoader(
        training_dataset,
        batch_size=batch_size,
        shuffle=True,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=batch_size,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PolicyCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    artifact_paths = build_model_artifact_paths(repo_root)

    history: list[dict[str, object]] = []
    best_validation_loss = float("inf")

    for epoch in range(1, epochs + 1):
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

        history.append(
            {
                "epoch": epoch,
                "train_loss": training_metrics.loss,
                "train_top1": training_metrics.top1_accuracy,
                "train_top3": training_metrics.top3_accuracy,
                "train_top5": training_metrics.top5_accuracy,
                "validation_loss": validation_metrics.loss,
                "validation_top1": validation_metrics.top1_accuracy,
                "validation_top3": validation_metrics.top3_accuracy,
                "validation_top5": validation_metrics.top5_accuracy,
                "validation_illegal_top1": validation_metrics.illegal_top1_rate,
            }
        )

        print(
            f"Epoch {epoch:02d} | "
            f"train loss={training_metrics.loss:.4f} | "
            f"val loss={validation_metrics.loss:.4f} | "
            f"top1={validation_metrics.top1_accuracy:.3%} | "
            f"top3={validation_metrics.top3_accuracy:.3%} | "
            f"top5={validation_metrics.top5_accuracy:.3%} | "
            f"illegal={validation_metrics.illegal_top1_rate:.3%}"
        )

        if validation_metrics.loss < best_validation_loss:
            best_validation_loss = validation_metrics.loss
            save_safetensors_checkpoint(model, artifact_paths.checkpoint_path)
            export_onnx_model(
                model,
                artifact_paths.onnx_path,
                opset_version=18,
            )

    write_model_metadata(
        artifact_paths.metadata_path,
        build_model_metadata_payload(
            onnx_opset=18,
            extra_fields={
                "artifact_stem": "policy_v1",
                "artifact_paths": {
                    "safetensors": artifact_paths.checkpoint_path.name,
                    "onnx": artifact_paths.onnx_path.name,
                    "metadata": artifact_paths.metadata_path.name,
                },
                "training_examples": len(training_examples),
                "validation_examples": len(validation_examples),
                "best_validation_loss": best_validation_loss,
            },
        ),
    )

    return {
        "history": history,
        "artifact_paths": artifact_paths,
        "best_validation_loss": best_validation_loss,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--learning-rate", type=float, default=LEARNING_RATE)
    parser.add_argument("--min-elo", type=int, default=MIN_ELO)
    parser.add_argument(
        "--validation-fraction", type=float, default=VALIDATION_FRACTION
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    repo_root = find_repo_root()

    run_training(
        repo_root=repo_root,
        sample_size=args.sample_size,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        min_elo=args.min_elo,
        validation_fraction=args.validation_fraction,
    )


if __name__ == "__main__":
    main()
