from click.testing import CliRunner
from assistant.main import cli

def test_assistant_test_body():
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "body"])
    assert result.exit_code == 0
    assert "Body Test" in result.output
    assert "Body status: OK" in result.output

def test_assistant_test_brain():
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "brain"])
    assert result.exit_code == 0
    assert "Brain Test" in result.output

def test_assistant_test_features():
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "features"])
    assert result.exit_code == 0
    assert "Feature Response Test" in result.output
