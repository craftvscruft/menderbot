import pytest
from click.testing import CliRunner
from menderbot.__main__ import cli, ask


@pytest.fixture
def runner():
    return CliRunner(env={"OPENAI_API_KEY": "test-override"})


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
    assert "Ask: \nBot: <LLM Output>" in result.output
