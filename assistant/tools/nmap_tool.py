import subprocess
from typing import Dict, Any
from assistant.tools.base import BaseTool

class NmapTool(BaseTool):
    @property
    def name(self) -> str:
        return "nmap"

    @property
    def description(self) -> str:
        return "Network exploration tool and security / port scanner."

