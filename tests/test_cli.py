import pytest
from click.testing import CliRunner

from menderbot.__main__ import ask, cli


@pytest.fixture
def runner(mock_embeddings):
    del mock_embeddings
    return CliRunner(
        env={"OPENAI_API_KEY": "sk-TEST00000000000000000000000000000000000000000000"}
    )


def test_noargs_shows_usage_message(runner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_ask_no_arg_fails(runner):
    result = runner.invoke(ask, [])
    assert result.exit_code == 1


def test_ask_shows_llm_output(runner):
    result = runner.invoke(ask, [], input="What's this code do??\n")
    assert not result.exception
    assert "Ask: \nBot: text text text text text" in result.output
