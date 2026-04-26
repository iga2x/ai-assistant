import shutil
from assistant.tools.detector import detect_tools, get_tool_version

def test_detect_tools():
    tools = detect_tools()
    assert len(tools) > 0
    # Python3 should be installed since we are running this test
    python_tool = next((t for t in tools if t.name == "python3"), None)
    assert python_tool is not None
    assert python_tool.installed is True
    assert python_tool.version != "unknown"

def test_missing_tool_handling():
    tools = detect_tools()
    # Check a tool that is likely missing (using a made-up name if needed, but let's look at COMMON_TOOLS)
    # subfinder or nuclei might be missing
    missing_tool = next((t for t in tools if not t.installed), None)
    if missing_tool:
        assert missing_tool.path == ""
        assert missing_tool.version == "unknown"

def test_tool_classification():
    tools = detect_tools()
    nmap = next((t for t in tools if t.name == "nmap"), None)
    if nmap:
        assert nmap.category == "scanner"
        assert nmap.risk_level == "medium"
