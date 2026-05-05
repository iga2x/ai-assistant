# tests/ai/test_response_parser.py
from assistant.ai.response_parser import ResponseParser
from assistant.ai.response_types_v2 import StructuredResponse

def test_parse_simple_response():
    text = """
Answer: Your local IP is 192.168.10.108.

Command / Example:
hostname -I

Details: This shows the IP addresses assigned to your machine.
"""
    parser = ResponseParser()
    result = parser.parse(text)
    assert isinstance(result, StructuredResponse)
    assert result.answer == "Your local IP is 192.168.10.108."
    assert result.command == "hostname -I"
    assert result.details == "This shows the IP addresses assigned to your machine."
    assert result.next_step is None

def test_parse_response_with_all_fields():
    text = """
Answer: Scan completed successfully.

Command / Example:
nmap -sT -p 1-1000 192.168.10.108

Details: Scanned ports 1-1000. Full logs available with /view.

Next step: Run a local listening-port check with ss -tulnp.
"""
    parser = ResponseParser()
    result = parser.parse(text)
    assert result.answer == "Scan completed successfully."
    assert result.command == "nmap -sT -p 1-1000 192.168.10.108"
    assert result.details == "Scanned ports 1-1000. Full logs available with /view."
    assert result.next_step == "Run a local listening-port check with ss -tulnp."

def test_parse_response_without_optional_fields():
    text = "Answer: Simple answer."
    parser = ResponseParser()
    result = parser.parse(text)
    assert result.answer == "Simple answer."
    assert result.command is None
    assert result.details is None
    assert result.next_step is None

def test_parse_response_with_code_blocks():
    text = """
Answer: Use this command.

Command / Example:
```bash
hostname -I
```

Details: This shows your IP.
"""
    parser = ResponseParser()
    result = parser.parse(text)
    assert result.answer == "Use this command."
    assert "hostname -I" in result.command
    assert result.details == "This shows your IP."

def test_parse_unstructured_response_fallback():
    text = "This is an unstructured response without any labeled fields."
    parser = ResponseParser()
    result = parser.parse(text)
    assert isinstance(result, StructuredResponse)
    assert result.answer == "This is an unstructured response without any labeled fields."
    assert result.command is None
