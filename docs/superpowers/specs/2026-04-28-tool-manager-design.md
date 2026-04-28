# Tool Management System Design

**Date:** 2026-04-28
**Status:** Design Complete (v2 - Patched)
**Priority:** High

## Overview

Intelligent tool management system for AI assistant. Automates detection, installation, and lifecycle management of security tools with proper safety guards, error handling, and user approval flows.

## Problem Statement

Current tool system has critical flaws:
- Wrong version detection commands (assetfinder, john, autopsy)
- Missing ecosystem metadata (apt, go, pip, cargo, binary)
- No automated installation capability
- Confuses "not detected" with "not installed"
- No dependency checking
- No safety guards for offensive tools
- Hard-coded metadata in detector.py (should be pure)
- No version constraints or compatibility checking
- No update mechanism
- No tool location awareness
- No install lock / concurrency control
- No persistent state / cache
- Static capability mapping

## Solution

Four-layer architecture with separation of concerns, structured error handling, and AI integration with approval guards.

---

## Architecture

### Four Layers

**Layer 0 - Data (Immutable)**
- `metadata.py` - CORE_TOOLS catalog (80-100 curated security tools)
- `custom_tools.yaml` - User additions (editable)
- `resolver.py` - Aliases, replacements, deprecated tools, bad entries

**Layer 1 - Detection (Read-Only, Pure)**
- `detector.py` - Detection engine
- `detect_tool(metadata)` → ToolInfo
- `detect_tools(metadata_list)` → List[ToolInfo]
- `get_tool_version(version_flags)` → str
- **Never performs installs, never writes**

**Layer 2 - Management (Orchestrator)**
- `manager.py` - ToolManager class
- Central API: detect(), list(), get_missing(), create_install_plan()
- Loads metadata (Layer 0)
- Calls detector (Layer 1)
- Calls resolver (Layer 0)
- Calls installer (Layer 3) **ONLY after approval**

**Layer 3 - Installation (Write)**
- `installer.py` - Ecosystem installers
- apt, go, pip/pipx, cargo, binary, manual-note
- Sudo handling, dependency checking
- **Never called from detector.py**

### File Structure

```
assistant/tools/
├── metadata.py          # CORE_TOOLS (data)
├── custom_tools.yaml    # User tools (data)
├── resolver.py          # Aliases/replacements (data transforms)
├── detector.py          # Pure detection (logic only)
├── manager.py           # Central API (orchestrator)
├── installer.py         # Installation (logic only)
└── [existing tool wrappers unchanged]
```

### Key Constraints

1. **Detector purity:** `detector.py` never calls `installer.py`
2. **Approval required:** All installs go through `manager.py` approval flow
3. **Metadata separation:** `CORE_TOOLS` in `metadata.py`, not `detector.py`
4. **Immutability:** Never mutate tool metadata inside functions

### Architectural Evolution

The current design provides a solid foundation. Future evolution toward a three-layer architecture:

**Current:** ToolManager (combined operations and selection)

**Future:**
- **ToolRegistry** - Pure data management (load, save, validate metadata)
- **ToolManager** - Operations (install, update, detect, cache)
- **ToolSelector** - AI decision layer (intelligent tool selection based on requirements)

This separation will enable:
- Easier testing of each component
- Pluggable selection strategies
- Better separation of data, operations, and AI logic

---

## Components & Data Flow

### Component 1: metadata.py (Data Layer)

```python
CORE_TOOLS = {
    "nmap": {
        "name": "nmap",
        "binary": "nmap",  # defaults to name if not specified
        "ecosystem": "apt",
        "install_cmd": "apt install nmap",
        "version_flags": ["--version", "-V"],
        "version_required": ">=7.0.0",
        "category": "scanner",
        "risk": "medium",
        "alternatives": [],
        "docs_url": "https://nmap.org/book/man.html",
        "deprecated": False,
        "priority": 10,
        "speed": "medium",
        "accuracy": "high"
    },
    "nuclei": {
        "name": "nuclei",
        "binary": "nuclei",
        "ecosystem": "go",
        "install_cmd": "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "version_flags": ["-version"],
        "version_required": ">=3.0.0",
        "category": "scanner",
        "risk": "high",
        "alternatives": [],
        "docs_url": "https://github.com/projectdiscovery/nuclei",
        "deprecated": False,
        "priority": 9,
        "speed": "fast",
        "accuracy": "high"
    },
    # ... 80-100 curated tools
}
```

**Fields:**
- **Required:** `name`, `ecosystem`, `install_cmd`, `version_flags`, `version_required`
- **Optional:** `binary`, `category`, `risk`, `alternatives`, `docs_url`, `deprecated`, `priority`, `speed`, `accuracy`

### Component 2: custom_tools.yaml (User Data)

```yaml
tools:
  my-custom-tool:
    name: "my-custom-tool"
    ecosystem: "binary"
    install_cmd: "cp /path/to/tool /usr/local/bin/"
    version_flags: ["--version"]
    category: "custom"
    risk: "low"
    alternatives: []
    docs_url: ""
    deprecated: false
```

### Component 3: resolver.py (Data Transforms)

```python
ALIASES = {"netcat": "nc"}
REPLACEMENTS = {
    "subjack": "subzy"  # deprecated → replacement
}
DEPRECATED = {
    "wifitex": "Custom tool, remove"
}
BAD_VERSION_CMDS = {
    "assetfinder": ["--help"],  # doesn't support --version
    "john": ["--list=build-info"],
    "autopsy": ["-h"],
    "dirsearch": ["--help"],
}
```

### Component 4: detector.py (Pure Detection)

```python
def detect_tool(metadata: Dict) -> ToolInfo:
    """Pure function. No side effects. No installs. Never mutates metadata."""
    binary = metadata.get("binary", metadata["name"])
    path = shutil.which(binary)

    if not path:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.NOT_FOUND
        )

    version = get_tool_version(binary, metadata["version_flags"])

    # Check if version meets requirements
    status = ToolStatus.INSTALLED
    if version != "unknown" and "version_required" in metadata:
        if not _meets_version_requirement(version, metadata["version_required"]):
            status = ToolStatus.OUTDATED

    return ToolInfo(
        name=metadata["name"],
        status=status,
        version=version,
        path=path
    )

def get_tool_version(binary: str, version_flags: List[str]) -> str:
    """Try multiple version flags in order."""
    for flag in version_flags:
        try:
            result = subprocess.run(
                [binary, flag],
                capture_output=True,
                timeout=2.0
            )
            if result.returncode == 0:
                return parse_version(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return "unknown"

def _meets_version_requirement(current: str, required: str) -> bool:
    """Check if current version meets requirement (e.g., '>=3.0.0')."""
    # Implementation using packaging.version or similar
    pass
```

### Component 5: installer.py (Install Handlers)

```python
def install_tool(tool: Dict) -> Result:
    """Install one tool. Called ONLY by manager.py."""
    ecosystem = tool["ecosystem"]

    if ecosystem == "apt":
        return install_apt(tool, sudo=True)
    elif ecosystem == "go":
        return install_go(tool)
    elif ecosystem == "pip":
        return install_pip(tool)  # prefers pipx
    elif ecosystem == "cargo":
        return install_cargo(tool)
    elif ecosystem == "binary":
        return install_binary(tool)
    elif ecosystem == "manual-note":
        return show_manual_instructions(tool)

def update_tool(tool: Dict) -> Result:
    """Update one tool to latest version."""
    ecosystem = tool["ecosystem"]

    if ecosystem == "apt":
        return update_apt(tool, sudo=True)
    elif ecosystem == "go":
        return update_go(tool)
    elif ecosystem == "pip":
        return update_pip(tool)
    elif ecosystem == "cargo":
        return update_cargo(tool)
    else:
        return Result(
            success=False,
            code=ErrorCode.NOT_FOUND,
            message=f"Update not supported for ecosystem: {ecosystem}"
        )

def update_apt(tool: Dict, sudo: bool) -> Result:
    cmd = f"{'sudo ' if sudo else ''}apt upgrade -y {tool['name']}"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Update failed",
            stderr=result.stderr.decode(),
            hint="Check apt repository or run 'apt update'"
        )

    return Result(success=True)

def update_go(tool: Dict) -> Result:
    cmd = f"go install -v github.com/projectdiscovery/{tool['name']}/v3/cmd/{tool['name']}@latest"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Go update failed",
            stderr=result.stderr.decode(),
            hint="Check Go installation and network connectivity"
        )

    return Result(success=True)

def update_pip(tool: Dict) -> Result:
    if shutil.which("pipx"):
        cmd = f"pipx upgrade {tool['name']}"
    else:
        cmd = f"pip3 install --upgrade --user {tool['name']}"

    result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Pip update failed",
            stderr=result.stderr.decode(),
            hint="Check Python environment"
        )

    return Result(success=True)

def update_cargo(tool: Dict) -> Result:
    cmd = f"cargo install {tool['name']} --force"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Cargo update failed",
            stderr=result.stderr.decode(),
            hint="Check Rust installation"
        )

    return Result(success=True)

def install_apt(tool: Dict, sudo: bool) -> Result:
    cmd = f"{'sudo ' if sudo else ''}apt install -y {tool['name']}"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Install failed",
            stderr=result.stderr.decode(),
            hint="Run 'apt update' and try again"
        )

    return Result(success=True)

def install_pip(tool: Dict) -> Result:
    """Prefer pipx over system pip."""
    if shutil.which("pipx"):
        cmd = f"pipx install {tool['name']}"
    else:
        cmd = f"pip3 install --user {tool['name']}"
    return run_install(cmd, sudo=False)
```

### Component 6: manager.py (Orchestrator)

```python
class ToolManager:
    def __init__(self):
        self.core_tools = load_metadata()
        self.custom_tools = load_yaml("custom_tools.yaml")
        self.installer = Installer()
        self.detector = Detector()
        self.resolver = Resolver()

        # Concurrency control
        self._install_lock = threading.Lock()

        # Persistent state
        self._cache_path = os.path.expanduser("~/.assistant/cache/tools.json")
        self._cache_ttl = 300  # 5 minutes
        self._failed_installs_path = os.path.expanduser("~/.assistant/cache/failed_installs.json")

    def detect(self, use_cache: bool = True) -> List[ToolInfo]:
        """Load metadata, call detector, return results. Never mutates metadata."""
        if use_cache:
            cached = self._load_cache()
            if cached:
                return cached

        all_tools = {**self.core_tools, **self.custom_tools}
        detected = []

        for name, metadata in all_tools.items():
            resolved = self.resolver.resolve(name)
            if resolved is None:  # deprecated without replacement
                continue

            # Create runtime copy, never mutate original metadata
            runtime_metadata = dict(metadata)
            runtime_metadata["name"] = resolved
            detected.append(self.detector.detect_tool(runtime_metadata))

        # Cache results
        self._save_cache(detected)

        return detected

    def get_missing(self, category: str = None) -> List[Dict]:
        """Filter uninstalled or outdated tools."""
        detected = self.detect()
        missing = [t for t in detected if t.status not in [ToolStatus.INSTALLED, ToolStatus.OUTDATED]]

        if category:
            missing = [t for t in missing if t.category == category]

        return [self._tool_info_to_dict(t) for t in missing]

    def get_outdated(self) -> List[Dict]:
        """Get tools that are installed but don't meet version requirements."""
        detected = self.detect()
        outdated = [t for t in detected if t.status == ToolStatus.OUTDATED]
        return [self._tool_info_to_dict(t) for t in outdated]

    def create_install_plan_for_categories(self, categories: List[str]) -> InstallPlan:
        """Create install plan for specific categories."""
        missing = self.get_missing()
        filtered = [t for t in missing if t["category"] in categories]
        return self._create_install_plan(filtered)

    def create_install_plan_for_tools(self, tool_names: List[str]) -> InstallPlan:
        """Create install plan for specific tools."""
        all_tools = {**self.core_tools, **self.custom_tools}
        filtered = []

        for name in tool_names:
            if name in all_tools:
                metadata = dict(all_tools[name])  # Copy, don't mutate
                metadata["name"] = self.resolver.resolve(name) or name
                filtered.append(metadata)

        return self._create_install_plan(filtered)

    def _create_install_plan(self, tools: List[Dict]) -> InstallPlan:
        """Create install plan from tool list. Never mutates input."""
        # Create runtime copies for dependency info
        runtime_tools = []
        for tool in tools:
            runtime_tool = dict(tool)
            deps = self._check_dependencies(runtime_tool)

            # Store dependency info in runtime copy only
            runtime_tool["dependencies_ok"] = deps.available
            runtime_tool["dependency_hint"] = deps.hint if not deps.available else ""
            runtime_tool["installer_hint"] = deps.installer_hint

            runtime_tools.append(runtime_tool)

        # Group by ecosystem
        grouped = self._group_by_ecosystem(runtime_tools)

        return InstallPlan(tools=grouped, total=len(runtime_tools))

    def update_tool(self, tool_name: str) -> Result:
        """Update a single tool to latest version."""
        metadata = self._get_tool_metadata(tool_name)
        if not metadata:
            return Result(success=False, code=ErrorCode.NOT_FOUND, message=f"Tool {tool_name} not found")

        with self._install_lock:
            result = self.installer.update_tool(metadata)
            if result.success:
                self._clear_cache()
            return result

    def update_all(self) -> Dict[str, Result]:
        """Update all installed tools."""
        detected = self.detect()
        installed = [t for t in detected if t.status == ToolStatus.INSTALLED]

        results = {}
        for tool in installed:
            results[tool.name] = self.update_tool(tool.name)

        self._clear_cache()
        return results

    def present_install_plan(self, plan: InstallPlan):
        """Show plan and get user approval."""
        print("\nMissing tools to install:")

        for ecosystem, tools in plan.tools.items():
            print(f"\n{ecosystem.upper()}: {', '.join(t['name'] for t in tools)}")

        choice = input("\nInstall all? [y/n/s] (s=select): ")

        if choice.lower() == "s":
            selected = self._interactive_select(plan.tools)
        elif choice.lower() == "y":
            selected = [t for tools in plan.tools.values() for t in tools]
        else:
            return

        self._execute_install(selected)

    def _execute_install(self, tools: List[Dict]):
        """Install with approval guard and concurrency control."""
        with self._install_lock:
            for tool in tools:
                # Safety check for high-risk tools
                if self._is_high_risk(tool):
                    if not self._get_approval([tool]):
                        print(f"Skipped {tool['name']} (high-risk usage tool, requires explicit approval)")
                        continue

                # Check dependencies
                deps = self._check_dependencies(tool)
            if not deps.available:
                print(f"Skipped {tool['name']}: {deps.hint}")
                continue

            # Install
            print(f"Installing {tool['name']}...")
            result = install_with_retry(tool)

            if result.success:
                print(f"✓ {tool['name']} installed")
            else:
                print(f"✗ {tool['name']} failed: {result.message}")
                if result.hint:
                    print(f"  Hint: {result.hint}")

        # Re-detect
        self.detect(use_cache=False)

    def _load_cache(self) -> Optional[List[ToolInfo]]:
        """Load cached detection results if not expired."""
        if not os.path.exists(self._cache_path):
            return None

        try:
            with open(self._cache_path, 'r') as f:
                data = json.load(f)

            cached_time = data.get('timestamp', 0)
            if time.time() - cached_time > self._cache_ttl:
                return None

            return [ToolInfo(**item) for item in data.get('tools', [])]
        except Exception:
            return None

    def _save_cache(self, tools: List[ToolInfo]):
        """Save detection results to cache."""
        try:
            os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)

            with open(self._cache_path, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'tools': [t.model_dump() for t in tools]
                }, f, indent=2)
        except Exception:
            pass

    def _clear_cache(self):
        """Clear cached detection results."""
        try:
            if os.path.exists(self._cache_path):
                os.remove(self._cache_path)
        except Exception:
            pass

    def _record_failed_install(self, tool_name: str, error: Result):
        """Record failed installation for future reference."""
        try:
            os.makedirs(os.path.dirname(self._failed_installs_path), exist_ok=True)

            failed = {}
            if os.path.exists(self._failed_installs_path):
                with open(self._failed_installs_path, 'r') as f:
                    failed = json.load(f)

            failed[tool_name] = {
                'error': error.code,
                'message': error.message,
                'last_attempt': time.time(),
                'retry_count': failed.get(tool_name, {}).get('retry_count', 0) + 1
            }

            with open(self._failed_installs_path, 'w') as f:
                json.dump(failed, f, indent=2)
        except Exception:
            pass

    def _get_failed_installs(self) -> Dict[str, Dict]:
        """Get history of failed installations."""
        try:
            if os.path.exists(self._failed_installs_path):
                with open(self._failed_installs_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
```

### Data Flow

```
User Request → manager.py
    → load metadata (metadata.py, custom_tools.yaml)
    → resolve tool names (resolver.py)
    → call detector (detector.py)
    → filter/group results
    → check dependencies
    → present install plan
    → get user approval
    → call installer (installer.py)
    → track progress
    → re-detect
    → report results
```

---

## Installation Workflow

### Complete Workflow

```
detect
  → resolve aliases/replacements
  → remove deprecated/bad entries
  → group by ecosystem
  → check dependencies
  → show selectable install plan
  → always ask approval
  → extra approval for high-risk offensive tools
  → install sequentially
  → re-detect
  → report installed / failed / skipped / manual
```

### Example Flow

```
User: "install missing tools"
  ↓
manager.install_batch()
  ↓
1. Detect all tools
2. Resolve: subjack → subzy, remove wifitex (deprecated)
3. Filter missing (not in PATH)
4. Group by ecosystem:
     APT: nmap, masscan, aircrack-ng, zaproxy, ncat
     GO: nuclei, subfinder, httpx, dnsx, subzy
     PIP/PIPX: dirsearch, volatility3
     CARGO: rustscan
     MANUAL: metasploit, burpsuite
5. Check dependencies:
     ✓ go (required for Go tools)
     ✓ cargo (required for Rust tools)
     ✓ pipx (will use for Python tools)
6. Show selectable install plan
7. User selects tools
8. SAFETY CHECK:
     - If tool is high-risk (metasploit, sqlmap, hydra) → FORCE explicit approval
     - Show: "⚠️ High-risk offensive tool. Installation requires explicit approval."
9. Ask: "Proceed with installation? [y/n]"
10. Install sequentially:
     - APT tools with sudo
     - GO/CARGO tools without sudo
     - PIPX tools without sudo (isolated)
     - MANUAL tools → show install instructions
11. Re-detect → report results
```

### Ecosystem Grouping (Corrected)

```
APT: nmap, masscan, aircrack-ng, zaproxy, ncat
GO: nuclei, subfinder, httpx, dnsx, subzy
PIP/PIPX: dirsearch, volatility3
CARGO: rustscan
MANUAL: metasploit, burpsuite
```

### Dependency Checking

```python
def _check_dependencies(self, tool: Dict) -> DependencyCheck:
    ecosystem = tool["ecosystem"]
    missing = []

    if ecosystem == "go" and not shutil.which("go"):
        missing.append("go (required for Go tools)")

    if ecosystem == "cargo" and not shutil.which("cargo"):
        missing.append("cargo (required for Rust tools)")

    if ecosystem == "pip":
        # Prefer pipx for isolation
        if shutil.which("pipx"):
            tool["installer_hint"] = "pipx"
        elif not shutil.which("pip3"):
            missing.append("pip3 (required for Python tools)")

    if missing:
        return DependencyCheck(
            available=False,
            missing=missing,
            hint=f"Install dependencies first: {' '.join(missing)}"
        )

    return DependencyCheck(available=True)
```

### Safety Rules

**High-risk tools require explicit approval:**
```python
HIGH_RISK_TOOLS = {"metasploit", "sqlmap", "hydra", "exploitdb"}

def _is_high_risk(self, tool: Dict) -> bool:
    return tool["name"].lower() in HIGH_RISK_TOOLS
```

**Never auto-install dangerous/offensive tools in any mode. All installs require explicit user approval.**

---

## Error Handling

### Structured Error Codes

```python
class ErrorCode:
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    INSTALL_FAILED = "install_failed"
    DEPENDENCY_MISSING = "dependency_missing"
    NETWORK_ERROR = "network_error"
    NOT_IN_PATH = "not_in_path"
    BROKEN = "broken"

class ToolStatus:
    INSTALLED = "installed"
    NOT_FOUND = "not_found"
    NOT_IN_PATH = "not_in_path"
    PERMISSION_DENIED = "permission_denied"
    BROKEN = "broken"
    OUTDATED = "outdated"

CRITICAL_ERRORS = {
    ErrorCode.PERMISSION_DENIED,
    ErrorCode.DEPENDENCY_MISSING,
}

RETRYABLE_ERRORS = {
    ErrorCode.TIMEOUT,
    ErrorCode.NETWORK_ERROR,
}
```

### Result Objects

```python
@dataclass
class Result:
    success: bool
    code: Optional[str] = None
    message: str = ""
    stderr: str = ""
    hint: str = ""

@dataclass
class ToolInfo:
    name: str
    status: str
    version: str = "unknown"
    path: str = ""
    error: str = ""
    hint: str = ""

@dataclass
class DependencyCheck:
    available: bool
    missing: List[str] = field(default_factory=list)
    hint: str = ""
    installer_hint: str = ""
```

### Detection Error Handling

```python
def detect_tool(metadata: Dict) -> ToolInfo:
    try:
        path = shutil.which(metadata["name"])
        if not path:
            return ToolInfo(
                name=metadata["name"],
                status=ToolStatus.NOT_FOUND
            )

        version = get_tool_version(metadata["version_flags"])
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.INSTALLED,
            version=version,
            path=path
        )

    except PermissionError:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.PERMISSION_DENIED,
            error="Permission denied",
            hint="Check file permissions"
        )

    except subprocess.TimeoutExpired:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.INSTALLED,
            version="timeout",
            warning="Tool unresponsive"
        )
```

### Installation Error Handling

```python
def install_apt(tool: Dict, sudo: bool) -> Result:
    cmd = f"{'sudo ' if sudo else ''}apt install -y {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Install failed",
                stderr=result.stderr.decode(),
                hint="Check apt repository or run 'apt update'"
            )

        return Result(success=True)

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Installation timeout",
            hint="Network issue or large package"
        )

    except PermissionError:
        return Result(
            success=False,
            code=ErrorCode.PERMISSION_DENIED,
            message="Permission denied",
            hint="Use sudo or run as root"
        )
```

### Retry Strategy

```python
def install_with_retry(tool: Dict, max_attempts: int = 2) -> Result:
    for attempt in range(max_attempts):
        result = installer.install_tool(tool)

        if result.success:
            return result

        if result.code not in RETRYABLE_ERRORS:
            break  # Don't retry non-retryable errors

    return result
```

### Batch Error Handling

```python
def install_batch(self, tools: List[Dict]):
    results = {
        "installed": [],
        "failed": [],
        "skipped": []
    }

    for tool in tools:
        try:
            # Check dependencies
            deps = self._check_dependencies(tool)
            if not deps.available:
                results["skipped"].append({
                    "tool": tool["name"],
                    "reason": deps.hint
                })
                continue

            # Install
            result = install_with_retry(tool)

            if result.success:
                results["installed"].append(tool["name"])
            else:
                results["failed"].append({
                    "tool": tool["name"],
                    "code": result.code,
                    "error": result.message,
                    "hint": result.hint
                })

                # Stop on critical errors
                if result.code in CRITICAL_ERRORS:
                    self._report_critical_failure(result)
                    return results

        except Exception as e:
            results["failed"].append({
                "tool": tool["name"],
                "error": f"Unexpected error: {str(e)}",
                "hint": "Check logs for details"
            })

    return results
```

### Error Hierarchy

1. **Critical** → Stop batch, report immediately (permission, missing dependencies)
2. **Warning** → Continue, log, show in summary (timeout, network error)
3. **Info** → Note, don't affect outcome (tool not in PATH)

---

## Testing Strategy

### Unit Tests

**test_detector.py**
- Test `detect_tool()` with mock metadata
- Test `get_tool_version()` with multiple version flags
- Test detection of installed vs missing tools
- Test permission denied handling
- Test timeout handling

**test_resolver.py**
- Test alias resolution
- Test deprecation handling
- Test replacement mapping
- Test bad version command overrides

**test_installer.py**
- Test apt installer with dry-run
- Test go installer
- Test pip/pipx preference
- Test cargo installer
- Test binary installer
- Test error code handling

**test_manager.py**
- Test workflow orchestration
- Test metadata loading
- Test filtering by category
- Test install plan creation
- Test approval guard

### Integration Tests

**test_tool_management.py**
- End-to-end: detect → install → verify
- Test batch installation
- Test custom tools YAML loading
- Test dependency checking flow

**test_yaml_loading.py**
- Load custom_tools.yaml
- Validate schema
- Test malformed YAML handling

### Test Doubles

```python
# Mock detection
def mock_which(tool):
    return f"/usr/bin/{tool}" if tool == "nmap" else None

# Mock installation
def mock_subprocess_run(cmd, **kwargs):
    return Mock(returncode=0, stdout=b"7.94")

# Fake YAML files
@pytest.fixture
def fake_yaml(tmp_path):
    yaml_file = tmp_path / "custom_tools.yaml"
    yaml_file.write_text("tools:\n  test:\n    name: test\n    ecosystem: apt\n    install_cmd: apt install test\n    version_flags:\n      - --version\n")
    return yaml_file
```

### Coverage Targets

- **Detector:** 95%+ (pure functions, easy to test)
- **Resolver:** 90%+ (data transformations)
- **Installer:** 80%+ (external deps, integration-heavy)
- **Manager:** 85%+ (orchestration logic)

---

## AI Integration

### ToolManager as AI Interface

```python
manager = ToolManager()

# "What tools do I have?"
available = manager.list_available()

# "What's missing for recon?"
missing = manager.get_missing(category="recon")

# "Suggest tools for port scanning"
suggested = manager.suggest_tools_for_capability("port_scan")
```

### Capability Mapping

```python
CAPABILITY_MAP = {
    "port_scan": {
        "nmap": {"priority": 10, "speed": "medium", "accuracy": "high"},
        "masscan": {"priority": 8, "speed": "fast", "accuracy": "medium"},
        "rustscan": {"priority": 7, "speed": "fast", "accuracy": "medium"}
    },
    "subdomain_enum": {
        "subfinder": {"priority": 10, "speed": "fast", "accuracy": "high"},
        "amass": {"priority": 9, "speed": "slow", "accuracy": "very_high"},
        "assetfinder": {"priority": 6, "speed": "fast", "accuracy": "medium"}
    },
    "vuln_scan": {
        "nuclei": {"priority": 10, "speed": "fast", "accuracy": "high"},
        "nikto": {"priority": 7, "speed": "medium", "accuracy": "medium"}
    },
    "web_fuzzing": {
        "ffuf": {"priority": 10, "speed": "fast", "accuracy": "high"},
        "gobuster": {"priority": 8, "speed": "medium", "accuracy": "high"},
        "dirsearch": {"priority": 6, "speed": "medium", "accuracy": "medium"}
    },
    "sql_injection": {
        "sqlmap": {"priority": 10, "speed": "medium", "accuracy": "high"}
    },
    "password_cracking": {
        "john": {"priority": 9, "speed": "medium", "accuracy": "high"},
        "hashcat": {"priority": 10, "speed": "fast", "accuracy": "high"},
        "hydra": {"priority": 8, "speed": "medium", "accuracy": "medium"}
    },
    "wifi_auditing": {
        "aircrack-ng": {"priority": 10, "speed": "medium", "accuracy": "high"},
        "wifite": {"priority": 9, "speed": "medium", "accuracy": "high"},
        "reaver": {"priority": 6, "speed": "slow", "accuracy": "medium"}
    },
    "memory_forensics": {
        "volatility": {"priority": 8, "speed": "medium", "accuracy": "high"},
        "volatility3": {"priority": 10, "speed": "medium", "accuracy": "high"}
    },
}

class ToolSelector:
    """AI decision layer for tool selection based on requirements."""

    def __init__(self, manager: ToolManager):
        self.manager = manager
        self.capability_map = CAPABILITY_MAP

    def select_best_tool(self, capability: str, preference: str = "balanced") -> Optional[str]:
        """
        Select best tool for a capability based on preference.

        preference: 'speed', 'accuracy', 'balanced'
        """
        if capability not in self.capability_map:
            return None

        tools = self.capability_map[capability]
        available = [t for t in tools.keys() if self.manager.is_available(t)]

        if not available:
            return None

        if preference == "speed":
            # Sort by speed (fast > medium > slow)
            speed_order = {"fast": 3, "medium": 2, "slow": 1}
            return max(available, key=lambda t: speed_order[tools[t]["speed"]])

        elif preference == "accuracy":
            # Sort by accuracy (very_high > high > medium)
            accuracy_order = {"very_high": 3, "high": 2, "medium": 1}
            return max(available, key=lambda t: accuracy_order[tools[t]["accuracy"]])

        else:  # balanced
            # Sort by priority
            return max(available, key=lambda t: tools[t]["priority"])

    def get_tools_by_capability(self, capability: str) -> List[str]:
        """Get all available tools for a capability."""
        if capability not in self.capability_map:
            return []

        return [t for t in self.capability_map[capability].keys()
                if self.manager.is_available(t)]

    def get_missing_tools_for_capability(self, capability: str) -> List[str]:
        """Get missing tools for a capability."""
        if capability not in self.capability_map:
            return []

        return [t for t in self.capability_map[capability].keys()
                if not self.manager.is_available(t)]
```

### AI Integration Rules

```python
# AI uses ToolSelector for intelligent tool selection
selector = ToolSelector(manager)

# AI can suggest best tool for capability
def suggest_best_tool(capability: str, preference: str = "balanced") -> Optional[str]:
    return selector.select_best_tool(capability, preference)

# AI can get all available tools for capability
def get_available_tools(capability: str) -> List[str]:
    return selector.get_tools_by_capability(capability)

# AI can create install plans for capabilities
def create_install_plan_for_capability(capability: str) -> InstallPlan:
    missing = selector.get_missing_tools_for_capability(capability)
    return manager.create_install_plan_for_tools(missing)

# AI CANNOT silently install tools
def install_tools_for_capability(capability: str):
    plan = create_install_plan_for_capability(capability)
    manager.present_install_plan(plan)  # User must approve
    # No direct install calls from AI
```

### Safety Layer

```python
def is_safe_to_run(self, tool_name: str) -> bool:
    """Check if tool is safe for AI to suggest/execute."""
    metadata = self.get_tool_metadata(tool_name)

    # High-risk tools require explicit approval
    if self._is_high_risk(tool_name):
        return False

    # Check if tool has valid scope
    if not self._has_valid_scope(tool_name):
        return False

    return True
```

### AI Integration Constraints

1. **AI can suggest tools** - Based on capability mapping
2. **AI can create install plans** - For user review
3. **AI cannot silently install tools** - All installs require manager approval flow
4. **High-risk tools always require approval** - Even in suggestions
5. **AI must check tool availability** - Before suggesting or running

### Planner Integration

```python
# Planner uses this interface
class ToolCapabilityLayer:
    def __init__(self):
        self.manager = ToolManager()

    def get_available_tools(self, capability: str) -> List[str]:
        """Get installed tools for a capability."""
        all_tools = CAPABILITY_MAP.get(capability, [])
        return [t for t in all_tools if self.manager.is_available(t)]

    def get_missing_tools(self, capability: str) -> List[str]:
        """Get missing tools for a capability."""
        all_tools = CAPABILITY_MAP.get(capability, [])
        return [t for t in all_tools if not self.manager.is_available(t)]

    def plan_tool_installation(self, capability: str) -> InstallPlan:
        """Create install plan for capability."""
        missing = self.get_missing_tools(capability)
        return self.manager.create_install_plan(missing)
```

---

## File Changes

### New Files

1. **assistant/tools/metadata.py** - CORE_TOOLS catalog (80-100 tools)
2. **assistant/tools/resolver.py** - Aliases, replacements, deprecated tools
3. **assistant/tools/manager.py** - ToolManager class
4. **assistant/tools/installer.py** - Ecosystem installers
5. **assistant/tools/custom_tools.yaml** - User additions (empty initially)

### Modified Files

1. **assistant/tools/detector.py**
   - Remove COMMON_TOOLS (move to metadata.py)
   - Make `detect_tool()` pure function
   - Add `get_tool_version()` with multiple flag support
   - Ensure NO install calls
   - Add structured error handling

2. **assistant/tools/runner.py**
   - Keep as-is (backward compatible)
   - Update imports if needed

### Unchanged Files

- All tool wrappers (nmap_tool.py, nuclei_tool.py, etc.)
- All other assistant modules

---

## Implementation Steps

1. **Create metadata.py** - Move and expand COMMON_TOOLS with full metadata
2. **Create resolver.py** - Implement aliases, replacements, deprecation handling
3. **Refactor detector.py** - Make pure, remove data, add structured errors
4. **Create installer.py** - Implement ecosystem installers
5. **Create manager.py** - Implement ToolManager class
6. **Create custom_tools.yaml** - Empty template
7. **Update imports** - Update runner.py if needed
8. **Write tests** - Unit tests for all components
9. **Integration test** - End-to-end workflow test
10. **Documentation** - Update CUSTOM_TOOLS.md, ADDING_TOOLS.md

---

## Success Criteria

1. ✅ Detector is pure (no install calls, no data ownership, no metadata mutation)
2. ✅ All 59+ core tools have correct metadata (version_required, binary, ecosystem)
3. ✅ Version detection works for all tools (correct flags, binary detection)
4. ✅ Installation works for all ecosystems (apt, go, pip, cargo, binary)
5. ✅ Update mechanism works (update_tool, update_all)
6. ✅ Dependency checking prevents failed installs
7. ✅ Safety guards prevent unauthorized high-risk tool installation
8. ✅ Batch approval flow works correctly
9. ✅ Error handling provides actionable feedback (structured codes)
10. ✅ Version constraint checking (OUTDATED status)
11. ✅ Tool location awareness (path stored in ToolInfo)
12. ✅ Install lock prevents concurrent installations
13. ✅ Cache layer with TTL (5 minutes)
14. ✅ Failure memory for learning from errors
15. ✅ AI can suggest tools and create plans but not silently install
16. ✅ ToolSelector for intelligent tool selection
17. ✅ Custom tools can be added via YAML
18. ✅ Tests achieve coverage targets
19. ✅ Backward compatible with existing tool wrappers

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wrong install commands | Tools fail to install | Test each ecosystem installer in CI |
| Version detection fails | Tools marked missing | Multiple version flags, fallback to `which` |
| Dependency missing | Install fails | Pre-check dependencies, show clear hints |
| User approves wrong tools | Security risk | High-risk tools require extra approval |
| YAML schema invalid | Custom tools fail | Validate schema on load, show errors |
| Path issues after install | Tool not found | Re-detect after install, show PATH hints |
| Sudo not available | APT installs fail | Check sudo availability, show alternative |

---

## Future Enhancements

1. **Auto-discovery** - Scan PATH for unknown tools, suggest additions to custom_tools.yaml
2. **Tool health checks** - Verify tools actually work (not just installed)
3. **Tool profiles** - Pre-defined tool sets for bug bounty, pentesting, forensics
4. **Installation presets** - Quick install of tool categories
5. **Uninstall capability** - Clean tool removal
6. **Tool verification** - Hash verification for downloaded binaries
7. **Advanced failure recovery** - Automatic retry strategies for known failures

---

## Sign-Off

Design complete and approved.

**Next Steps:**
1. Write implementation plan using writing-plans skill
2. Begin implementation following plan
3. Test at each milestone
4. Update documentation
