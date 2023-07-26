from unittest.mock import patch

import pytest


@pytest.fixture()
def mock_embeddings():
    with patch(
        "llama_index.embeddings.OpenAIEmbedding._get_text_embeddings",
        side_effect=mock_get_text_embeddings,
    ):
        with patch(
            "llama_index.embeddings.OpenAIEmbedding._get_text_embedding",
            side_effect=mock_get_text_embedding,
        ):
            yield


def mock_get_text_embedding(text: str) -> list[float]:
    """Mock get text embedding."""
    if text == "Hello world.":
        return [1, 0, 0, 0, 0]
    elif text == "This is a test.":
        return [0, 1, 0, 0, 0]
    else:
        raise ValueError("Invalid text for `mock_get_text_embedding`.")


def mock_get_text_embeddings(texts: list[str]) -> list[list[float]]:
    """Mock get text embeddings."""
    return [mock_get_text_embedding(text) for text in texts]
