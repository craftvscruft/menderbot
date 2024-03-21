import os
from unittest.mock import patch

import pytest


@pytest.fixture()
def mock_embeddings():
    with patch(
        "llama_index.embeddings.openai.OpenAIEmbedding._get_text_embeddings",
        side_effect=mock_get_text_embeddings,
    ):
        with patch(
            "llama_index.embeddings.openai.OpenAIEmbedding._get_text_embedding",
            side_effect=mock_get_text_embedding,
        ):
            yield


@pytest.fixture(autouse=True)
def mock_settings_env_vars():
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "sk-TEST00000000000000000000000000000000000000000000"},
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


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests that call OpenAI",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as skipped by default")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
