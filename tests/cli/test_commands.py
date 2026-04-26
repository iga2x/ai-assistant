from click.testing import CliRunner
from assistant.main import cli

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "AI Assistant" in result.output

def test_cli_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "System Overview" in result.output
    assert "AI Providers" in result.output

def test_cli_ai_scan():
    runner = CliRunner()
    result = runner.invoke(cli, ["ai", "scan"])
    assert result.exit_code == 0
    assert "AI Provider Scan Results" in result.output

def test_cli_tools_scan():
    runner = CliRunner()
    result = runner.invoke(cli, ["tools", "scan"])
    assert result.exit_code == 0
    assert "Tool Detection Results" in result.output

def test_cli_doctor():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Diagnostic Check" in result.output
