"""Test PersistentShell execution integrity (System Runtime Audit)."""

import pytest
import time
from assistant.system.persistent_shell import PersistentShell


class TestPersistentShellExecutionIntegrity:
    """Test that PersistentShell guarantees execution integrity."""

    @pytest.fixture
    def shell(self):
        """Create a fresh shell for each test."""
        shell = PersistentShell()
        yield shell
        shell.close()

    def test_sequential_commands_no_mixing(self, shell):
        """Test that sequential commands don't mix output."""
        # Execute first command
        result1 = shell.execute("echo 'first'", timeout=5)
        assert result1["success"] is True
        assert "first" in result1["stdout"]
        assert "second" not in result1["stdout"]

        # Execute second command
        result2 = shell.execute("echo 'second'", timeout=5)
        assert result2["success"] is True
        assert "second" in result2["stdout"]
        assert "first" not in result2["stdout"]

        # Verify no marker leakage
        assert "---CMD_END_" not in result1["stdout"]
        assert "---CMD_END_" not in result2["stdout"]
        assert "$?" not in result1["stdout"]
        assert "$?" not in result2["stdout"]

    def test_exit_code_correctness(self, shell):
        """Test that exit codes are captured correctly."""
        # Success case
        result = shell.execute("true", timeout=5)
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "$?" not in result["stdout"]

        # Failure case
        result = shell.execute("false", timeout=5)
        assert result["success"] is False
        assert result["returncode"] == 1
        assert "$?" not in result["stdout"]

        # Custom exit code
        result = shell.execute("exit 42", timeout=5)
        assert result["success"] is False
        assert result["returncode"] == 42
        assert "$?" not in result["stdout"]

    def test_multiline_output_complete(self, shell):
        """Test that all lines of output are captured."""
        result = shell.execute("printf 'a\\nb\\nc\\n'", timeout=5)
        assert result["success"] is True
        assert "a" in result["stdout"]
        assert "b" in result["stdout"]
        assert "c" in result["stdout"]
        # Verify we have all three lines
        lines = result["stdout"].strip().split('\n')
        assert len(lines) == 3
        assert lines == ["a", "b", "c"]

    def test_delayed_output_captured(self, shell):
        """Test that delayed output is captured completely."""
        result = shell.execute("sh -c 'sleep 0.2; echo delayed'", timeout=10)
        assert result["success"] is True
        assert "delayed" in result["stdout"]
        # Should have waited for the delayed output
        assert result["stdout"].strip() == "delayed"

    def test_large_output_complete(self, shell):
        """Test that large output is captured completely."""
        result = shell.execute("seq 1 1000", timeout=10)
        assert result["success"] is True
        # Check we have the beginning and end
        assert "1" in result["stdout"]
        assert "1000" in result["stdout"]
        # Count lines to ensure we got all 1000
        lines = result["stdout"].strip().split('\n')
        assert len(lines) == 1000

    def test_no_prompt_artifacts(self, shell):
        """Test that shell prompt doesn't appear in output."""
        result = shell.execute("echo 'test'", timeout=5)
        assert result["success"] is True
        # Should not contain typical bash prompt patterns
        assert not any(prompt in result["stdout"] for prompt in [
            "user@hostname", "$", "#", "["
        ])
        # Should just contain the command output
        assert result["stdout"].strip() == "test"

    def test_command_with_colon_output(self, shell):
        """Test that commands with colons in output work correctly."""
        # Command that produces output with colons (like paths)
        result = shell.execute("echo '/path/to:file'", timeout=5)
        assert result["success"] is True
        assert "/path/to:file" in result["stdout"]
        # Should not interfere with exit code parsing
        assert "$?" not in result["stdout"]
        assert "---CMD_END_" not in result["stdout"]

    def test_empty_output_handling(self, shell):
        """Test that commands with no output are handled correctly."""
        result = shell.execute("true", timeout=5)
        assert result["success"] is True
        # Empty output is valid
        assert result["stdout"] == ""
        assert "$?" not in result["stdout"]

    def test_command_with_special_chars(self, shell):
        """Test commands with special characters don't break parsing."""
        result = shell.execute("echo 'test$pecial'", timeout=5)
        assert result["success"] is True
        assert "test$pecial" in result["stdout"]
        assert "$?" not in result["stdout"]

    def test_concurrent_marker_uniqueness(self, shell):
        """Test that markers are unique per command."""
        results = []
        for i in range(5):
            result = shell.execute(f"echo 'command{i}'", timeout=5)
            results.append(result)
            assert result["success"] is True
            assert f"command{i}" in result["stdout"]

        # Verify all results are separate and complete
        for i, result in enumerate(results):
            assert f"command{i}" in result["stdout"]
            # No other command's output should be present
            for j in range(5):
                if j != i:
                    assert f"command{j}" not in result["stdout"]


class TestPersistentShellMarkerLogic:
    """Test the marker detection and parsing logic."""

    @pytest.fixture
    def shell(self):
        """Create a fresh shell for each test."""
        shell = PersistentShell()
        yield shell
        shell.close()

    def test_marker_not_in_stdout(self, shell):
        """Test that the marker never appears in final stdout."""
        for i in range(10):
            result = shell.execute(f"echo 'test{i}'", timeout=5)
            assert "---CMD_END_" not in result["stdout"]
            assert "$?" not in result["stdout"]

    def test_exit_code_extraction_accuracy(self, shell):
        """Test that exit codes are extracted accurately."""
        test_cases = [
            (0, "true"),
            (1, "false"),
            (2, "exit 2"),
            (127, "nonexistent_command_12345"),
        ]

        for expected_code, command in test_cases:
            result = shell.execute(command, timeout=5)
            # For non-existent commands, the shell might return 127
            if "nonexistent_command" in command:
                assert result["returncode"] in [127, 126]  # shell might use 126
            else:
                assert result["returncode"] == expected_code

            # Verify no marker or $? in stdout
            assert "---CMD_END_" not in result["stdout"]
            assert "$?" not in result["stdout"]

    def test_command_echo_doesnt_confuse_marker(self, shell):
        """Test that echo commands don't confuse marker detection."""
        # Command that echoes text similar to marker
        result = shell.execute("echo '---CMD_END_FAKE---'", timeout=5)
        assert result["success"] is True
        # The fake marker should be in output (it's real echo output)
        assert "---CMD_END_FAKE---" in result["stdout"]
        # But the real marker should not be
        assert result["stdout"].count("---CMD_END_") == 1  # Only the fake one


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
