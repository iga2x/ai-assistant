"""Test multi-task decomposition with comma pattern."""

import re


def test_comma_pattern_basic():
    """Test basic comma separation."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "find my ip, scan it"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    assert len(sub_inputs) == 2
    assert sub_inputs[0] == "find my ip"
    assert sub_inputs[1] == "scan it"


def test_comma_pattern_with_and():
    """Test comma with 'and' doesn't double split."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "find my ip and scan it"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    assert len(sub_inputs) == 2
    assert sub_inputs[0] == "find my ip"
    assert sub_inputs[1] == "scan it"


def test_comma_pattern_then():
    """Test 'then' separator."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "scan localhost then save result"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    assert len(sub_inputs) == 2
    assert sub_inputs[0] == "scan localhost"
    assert sub_inputs[1] == "save result"


def test_comma_pattern_comma_then():
    """Test comma followed by 'then' doesn't split twice."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "scan it, then save it"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    # Should split on comma, then strip trailing punctuation
    sub_inputs = [s.strip().rstrip(',;') for s in sub_inputs if s.strip()]
    assert len(sub_inputs) == 2
    assert sub_inputs[0] == "scan it"
    assert sub_inputs[1] == "then save it"


def test_comma_pattern_multiple_commas():
    """Test multiple comma-separated tasks."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "find ip, scan it, save result"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    assert len(sub_inputs) == 3
    assert sub_inputs[0] == "find ip"
    assert sub_inputs[1] == "scan it"
    assert sub_inputs[2] == "save result"


def test_comma_pattern_single_task():
    """Test single task without separators."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "scan 192.168.1.1"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    assert len(sub_inputs) == 1
    assert sub_inputs[0] == "scan 192.168.1.1"


def test_comma_pattern_trailing_comma():
    """Test trailing comma doesn't create empty task."""
    task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

    text = "scan it,"
    sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

    # Should handle trailing comma gracefully
    sub_inputs = [s.strip().rstrip(',;') for s in sub_inputs if s.strip()]
    assert len(sub_inputs) >= 1
    assert sub_inputs[0] == "scan it"
