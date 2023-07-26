import pytest
from click.testing import CliRunner

from menderbot.__main__ import ask, cli


@pytest.fixture
def runner(mock_embeddings):
    del mock_embeddings
    return CliRunner()


def test_noargs_shows_usage_message(runner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output
