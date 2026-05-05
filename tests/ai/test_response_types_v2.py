# tests/ai/test_response_types_v2.py
from assistant.ai.response_types_v2 import StructuredResponse, ResponseField

def test_structured_response_creation():
    response = StructuredResponse(
        answer="Your local IP is 192.168.10.108",
        command="hostname -I",
        details="This shows the IP addresses assigned to your machine.",
        next_step="Try checking your network configuration?"
    )
    assert response.answer == "Your local IP is 192.168.10.108"
    assert response.command == "hostname -I"
    assert response.details == "This shows the IP addresses assigned to your machine."
    assert response.next_step == "Try checking your network configuration?"

def test_structured_response_with_optional_fields():
    response = StructuredResponse(answer="Simple answer")
    assert response.answer == "Simple answer"
    assert response.command is None
    assert response.details is None
    assert response.next_step is None

def test_response_field_validation():
    field = ResponseField(name="answer", content="test content", required=True)
    assert field.name == "answer"
    assert field.content == "test content"
    assert field.required is True
