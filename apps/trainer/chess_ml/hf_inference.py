"""Hugging Face inference client for the chess policy model."""

from __future__ import annotations

import httpx

from chess_ml.inference import MovePrediction


class HuggingFacePolicyPredictor:
    """Generate chess move predictions using a remote Hugging Face endpoint."""

    def __init__(
        self,
        endpoint_url: str,
        *,
        token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.endpoint_url = endpoint_url

        headers: dict[str, str] = {}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        self.client = httpx.Client(
            headers=headers,
            timeout=timeout_seconds,
        )

    def predict(
        self,
        fen: str,
    ) -> MovePrediction:
        """Predict one move from a FEN position using Hugging Face."""

        response = self.client.post(
            self.endpoint_url,
            json={
                "fen": fen,
            },
        )

        response.raise_for_status()

        payload = response.json()

        return MovePrediction(
            from_square=payload["from_square"],
            to_square=payload["to_square"],
            promotion=payload.get("promotion"),
            score=float(payload["score"]),
            model_version=payload["model_version"],
        )
