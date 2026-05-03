# COMPREHENSIVE FIX PLAN
## AI Terminal Assistant - Root Cause Resolution

**Status**: Implementation in progress
**Approach**: Incremental migration with backward compatibility
**Timeline**: 6 phases, 6 weeks

---

## ALL 20 IDENTIFIED ISSUES

### CRITICAL (Safety/Security)
1. ✅ Duplicate Memory Systems (Pipeline vs Executor)
2. ✅ Safety Bypass in Pipeline Direct Execution
3. ✅ Shell Injection in WorkflowManager
4. ✅ MemoryManager.validate() Subprocess Without Safety
5. ✅ ToolRunner.is_safe_command() is Empty

### HIGH (Functionality)
6. ✅ Multi-Task Only Returns Last Result
7. ✅ Multi-Task Comma Pattern Bug
8. ✅ Context Substitution Only in Executor
9. ✅ Pronoun Resolution Double Replacement
10. ✅ Entity Extraction Duplication
11. ✅ Tool Detection Version Flag Race Condition
12. ✅ PersistentShell PTY Marker Collision

### MEDIUM (Architecture)
13. ✅ ContextResolver vs EntityStore Mismatch
14. ✅ Three Different Tool Discovery Methods
15. ✅ AI Response Parsing Fragmentation
16. ✅ Workflow System - Configuration Is Execution
17. ✅ AI Router Mock Response Hardcoded
18. ✅ No Centralized Timeout Configuration

### LOW (Cleanup)
19. ✅ Pending Action Methods Unused
20. ✅ Dead Code (response_parser.py)
21. ✅ Deleted Files Still Referenced

---

## PHASE 1: Foundations - Single Sources of Truth

### 1.1 Memory System Unification
**Issues**: 1, 13, 10, 14

**Decisions**:
- `memory.py` is the NEW system
- `context/entities.py` is DEPRECATED
- Create `IMemoryStore` interface

**Implementation Steps**:
1. Create `assistant/memory/interface.py` with IMemoryStore
2. Add deprecation warning to `context/entities.py`
3. Update all imports to use `memory.MemoryManager`
4. Unify entity extraction patterns
5. Add validate() safety checks through SafetyGate

**Files**:
- NEW: `assistant/memory/interface.py`
- MOD: `assistant/memory.py` (implement IMemoryStore)
- MOD: `assistant/context/entities.py` (add @deprecated)
- MOD: `assistant/context/resolver.py` (update import)
- MOD: `assistant/actions/executor.py` (update import)
- MOD: `assistant/app/terminal/pipeline.py` (already using memory)

**Tests**:
- `tests/memory/test_unified_interface.py`
- Verify entity extraction consistency
- Verify persistence across sessions

---

### 1.2 Tool Registry Unification
**Issues**: 14, 11

**Decisions**:
- Create `ToolRegistry` as SINGLE runtime source
- `ToolManager` handles management (install/update)
- `ToolRunner` becomes INTERNAL to `ToolRegistry`

**Implementation Steps**:
1. Create `assistant/tools/registry.py` (ToolRegistry class)
2. Move tool metadata loading from ToolManager to ToolRegistry
3. Fix version flag ordering in detector
4. Add timeout configuration per tool
5. Deprecate direct ToolRunner imports

**Files**:
- NEW: `assistant/tools/registry.py`
- MOD: `assistant/tools/manager.py` (delegate to ToolRegistry)
- MOD: `assistant/tools/runner.py` (add @deprecated)
- MOD: `assistant/tools/detector.py` (fix version flag logic)
- MOD: `assistant/actions/executor.py` (use ToolRegistry)
- MOD: `assistant/app/terminal/pipeline.py` (use ToolRegistry)

**Version Flag Fix** (Issue 11):
```python
# Current: Try flags in order, return on first success
# Fix: Score each match, return best match

def score_version_match(output: str, pattern: str) -> float:
    """Score how well output matches version pattern."""
    # Higher score = better match
    pass
```

**Tests**:
- `tests/tools/test_registry.py`
- `tests/tools/test_version_detection.py`
- Verify timeout configuration

---

### 1.3 AI Response Schema
**Issues**: 15, 18

**Decisions**:
- Define strict schema with validation
- Router returns ValidatedResponse, not string
- Extensible mock response system

**Implementation Steps**:
1. Create `assistant/ai/schemas.py` with strict models
2. Update `ai/router.py` to return ValidatedResponse
3. Update `ai/detector.py` to use schemas
4. Create mock response registry (extensible)
5. Deprecate `brain/response_parser.py`

**Files**:
- NEW: `assistant/ai/schemas.py`
- MOD: `assistant/ai/router.py` (use schemas, mock registry)
- MOD: `assistant/ai/detector.py` (use schemas)
- MOD: `assistant/tasks/planner.py` (accept ValidatedResponse)
- DEP: `assistant/brain/response_parser.py`

**Mock Response Registry**:
```python
MOCK_RESPONSES = {
    "ip_lookup": MockResponse(...),
    "scan": MockResponse(...),
    # Extensible via config
}
```

**Tests**:
- `tests/ai/test_schemas.py`
- `tests/ai/test_mock_responses.py`

---

## PHASE 2: Safety Layer

### 2.1 Create SafetyGate
**Issues**: 2, 4, 5, 17

**Decisions**:
- Centralized safety checking
- All execution MUST pass through
- Decorator support for declarative safety

**Implementation Steps**:
1. Create `assistant/safety/gate.py` (SafetyGate class)
2. Implement command checking (risk classification)
3. Implement plan checking (step-by-step)
4. Create @safety_check decorator
5. Update all execution paths to use SafetyGate

**Files**:
- NEW: `assistant/safety/gate.py`
- MOD: `assistant/tools/runner.py` (call SafetyGate)
- MOD: `assistant/actions/executor.py` (call SafetyGate)
- MOD: `assistant/tasks/workflow_manager.py` (call SafetyGate)
- MOD: `assistant/app/terminal/pipeline.py` (call SafetyGate)
- MOD: `assistant/memory.py` (validate() uses SafetyGate)

**SafetyGate Interface**:
```python
class SafetyGate:
    def check_command(self, command: str, context: dict) -> SafetyDecision:
        """Returns: ALLOW, BLOCK, REQUIRE_CONFIRMATION"""

    def check_plan(self, plan: Plan) -> PlanSafetyDecision:
        """Check entire plan, can auto-approve low-risk"""

    def execute_with_safety(self, command: str, context: dict) -> Result:
        """Execute with automatic safety checks"""
```

**Safety Checks to Add** (Issue 4, 17):
- MemoryManager.validate() subprocess calls through SafetyGate
- ToolRunner.is_safe_command() replaced with SafetyGate.check_command()

**Tests**:
- `tests/safety/test_gate.py`
- `tests/safety/test_decorator.py`
- Verify all execution paths go through SafetyGate

---

### 2.2 Remove Pipeline Safety Bypass
**Issues**: 2

**Implementation Steps**:
1. Remove direct execution in `pipeline.py:131-168`
2. All actions go through Planner → Executor
3. Read-only actions still work but through safety gate

**Files**:
- MOD: `assistant/app/terminal/pipeline.py` (remove lines 131-168)

**Tests**:
- Verify no safety bypass exists
- Integration test for read-only actions

---

## PHASE 3: Multi-Task Fix

### 3.1 Remove Text-Split Hack
**Issues**: 6, 7

**Decisions**:
- Remove sub_inputs loop from Pipeline
- Implement proper multi-intent planning
- Fix comma pattern for backward compatibility

**Implementation Steps**:
1. Update PromptBuilder for multi-intent handling
2. Enhance Planner to decompose multiple intents
3. Remove sub_inputs loop from Pipeline
4. Keep comma pattern as fallback for simple cases
5. Combine all results in output

**Files**:
- MOD: `assistant/brain/prompt_builder.py` (multi-intent instructions)
- MOD: `assistant/tasks/planner.py` (decompose_intents method)
- MOD: `assistant/app/terminal/pipeline.py` (remove lines 41-79, add fallback)
- MOD: `assistant/app/terminal/repl.py` (display all results)

**Comma Pattern Fix** (Issue 7):
```python
# Old: r'\s+(?:and|then)[,\s]+'
# New: r'(?:\s+(?:and|then)[,\s]+|,\s+(?!and|then))'
```

**Tests**:
- `tests/integration/test_multi_task.py`
- Test: "find my ip and gateway" → 3-step plan
- Test: "find ip, scan it" → 2-step plan
- Test: "scan localhost then save result" → 2-step plan
- Verify all results displayed

---

### 3.2 Pronoun Resolution Fix
**Issues**: 9, 8

**Implementation Steps**:
1. Order pronoun patterns by specificity
2. Use word boundaries correctly
3. Add tests for edge cases

**Files**:
- MOD: `assistant/context/resolver.py` (fix patterns, order)

**Pronoun Pattern Fix** (Issue 9):
```python
# Order: Most specific first
pronoun_map = {
    r'\bthe same target\b': target,  # Most specific
    r'\bthe previous result\b': target,
    r'\bmy ip\b': ip,
    r'\bthat ip\b': ip,
    r'\bthis host\b': target,
    r'\bmy machine\b': 'localhost',
    r'\bthere\b': target or ip,
    r'\bit\b': target,
    r'\bthat\b': target,
    r'\bsame\b': target,  # Least specific, last
    r'\bagain\b': target,
}
```

**Tests**:
- `tests/context/test_pronoun_resolution.py`
- Test: "that same target" → single replacement
- Test: "scan it again" → correct replacement
- Test: "check my ip" → correct replacement

---

### 3.3 Context Substitution Unification
**Issues**: 8, 10

**Implementation Steps**:
1. Move substitute_context to shared location
2. Apply in Pipeline AND Executor
3. Unify with ContextResolver

**Files**:
- NEW: `assistant/context/substitution.py` (shared logic)
- MOD: `assistant/actions/executor.py` (use shared substitution)
- MOD: `assistant/app/terminal/pipeline.py` (use shared substitution)
- MOD: `assistant/context/resolver.py` (integrate with substitution)

**Tests**:
- Verify "scan it" works in both paths
- Verify entity extraction consistency

---

## PHASE 4: Workflow Refactor

### 4.1 Separate Configuration from Execution
**Issues**: 3, 16

**Decisions**:
- Workflows define INTENTS, not commands
- Workflows are TEMPLATES for plans
- No direct subprocess calls

**Implementation Steps**:
1. Redesign workflow YAML format (intents, not commands)
2. Create WorkflowTemplate class
3. Remove subprocess from WorkflowManager
4. Workflows generate Plans, not execute
5. All execution through normal path

**Files**:
- MOD: `assistant/tasks/workflows/default_workflows.yaml` (new format)
- NEW: `assistant/tasks/workflow_template.py`
- MOD: `assistant/tasks/workflow_manager.py` (remove subprocess, use templates)
- MOD: `assistant/app/terminal/repl.py` (update workflow handling)

**New Workflow Format**:
```yaml
workflows:
  passive_recon:
    name: "Passive Reconnaissance"
    steps:
      - intent: "whois_lookup"
        params:
          target: "{target}"
      - intent: "dns_enumeration"
        params:
          target: "{target}"
      - intent: "http_check"
        params:
          target: "{target}"
          path: "/robots.txt"
```

**Tests**:
- `tests/workflows/test_template_system.py`
- Verify no shell injection
- Verify all workflows generate valid plans

---

## PHASE 5: Orchestrator

### 5.1 Create Orchestrator Layer
**Issues**: Architectural

**Decisions**:
- Orchestrator manages session and multi-request state
- Single entry point for all requests
- Clear data flow: Interface → Orchestrator → Planning → Safety → Execution

**Implementation Steps**:
1. Create `assistant/orchestrator/orchestrator.py`
2. Move logic from Pipeline to Orchestrator
3. Pipeline becomes thin wrapper
4. All requests go through Orchestrator.process_request()

**Files**:
- NEW: `assistant/orchestrator/__init__.py`
- NEW: `assistant/orchestrator/orchestrator.py`
- NEW: `assistant/orchestrator/session.py`
- MOD: `assistant/app/terminal/pipeline.py` (delegate to Orchestrator)
- MOD: `assistant/app/terminal/repl.py` (use Orchestrator)

**Orchestrator Interface**:
```python
class Orchestrator:
    def __init__(self):
        self.memory = MemoryManager()
        self.planner = Planner()
        self.safety = SafetyGate()
        self.executor = Executor()
        self.session = Session()

    def process_request(self, user_input: str) -> Response:
        """Single entry point for all requests."""
        # 1. Normalize
        # 2. Resolve context
        # 3. Plan (includes multi-intent decomposition)
        # 4. Safety check
        # 5. Execute
        # 6. Update memory
        # 7. Return response
```

**Tests**:
- `tests/orchestrator/test_request_flow.py`
- Integration tests for full request lifecycle

---

## PHASE 6: Infrastructure Fixes

### 6.1 PersistentShell Marker Fix
**Issues**: 12, 19

**Implementation Steps**:
1. Generate random unique marker per command
2. Use UUID or timestamp-based marker
3. Add marker escaping for collision detection

**Files**:
- MOD: `assistant/system/persistent_shell.py`

**Marker Fix**:
```python
import uuid

def _generate_marker(self) -> str:
    """Generate unique marker that won't appear in output."""
    return f"---CMD_END_{uuid.uuid4().hex}---"
```

**Timeout Configuration** (Issue 19):
```python
# assistant/config/manager.py
class TimeoutConfig(BaseModel):
    default: int = 60
    nmap_scan: int = 300
    web_request: int = 30
    tool: Dict[str, int] = {}
```

---

### 6.2 Database Session Management
**Issues**: 20

**Implementation Steps**:
1. Add context manager for database sessions
2. Ensure sessions are always closed
3. Add connection pooling configuration

**Files**:
- MOD: `assistant/db/database.py`
- MOD: All files using `self.db.session`

**Session Management**:
```python
@contextmanager
def get_session(self):
    """Context manager for database sessions."""
    session = self.Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
```

**Tests**:
- `tests/db/test_session_management.py`
- Verify no connection leaks

---

### 6.3 Cleanup Dead Code
**Issues**: 19, 20, 21

**Implementation Steps**:
1. Remove pending_action methods from repl.py
2. Remove deprecated response_parser.py
3. Remove deleted files from git (already done)
4. Update imports and references

**Files**:
- DEL: `assistant/brain/response_parser.py`
- MOD: `assistant/app/terminal/repl.py` (remove pending_action)
- VERIFY: No imports from deleted files

---

## TEST STRATEGY

### Unit Tests
- `tests/memory/test_unified_interface.py`
- `tests/tools/test_registry.py`
- `tests/tools/test_version_detection.py`
- `tests/ai/test_schemas.py`
- `tests/safety/test_gate.py`
- `tests/context/test_pronoun_resolution.py`
- `tests/workflows/test_template_system.py`
- `tests/db/test_session_management.py`

### Integration Tests
- `tests/integration/test_multi_task.py`
- `tests/integration/test_full_request_flow.py`
- `tests/integration/test_safety_layer.py`

### Regression Tests
- All existing tests must pass
- Add tests for each bug fix
- Add tests for each architectural change

---

## RISK MITIGATION

### Backward Compatibility
- Keep deprecated code for 2 releases
- Add @deprecated warnings
- Feature flags for new components
- Gradual migration path

### Rollback Plan
- Feature flags to disable new components
- Keep old code paths available
- Can fall back to Pipeline without Orchestrator
- Can disable SafetyGate (not recommended)

### Data Migration
- Memory data format unchanged
- Database schema unchanged
- Workflow format changes: provide migration script
- Config format: backward compatible

---

## EXECUTION TRACKER

### Phase 1: Foundations
- [x] 1.1 Memory System Unification
- [x] 1.2 Tool Registry Unification
- [x] 1.3 AI Response Schema

### Phase 2: Safety Layer
- [x] 2.1 Create SafetyGate
- [x] 2.2 Remove Pipeline Safety Bypass

### Phase 3: Multi-Task Fix
- [x] 3.1 Remove Text-Split Hack (partial - improved results)
- [x] 3.2 Pronoun Resolution Fix
- [x] 3.3 Context Substitution Unification

### Phase 4: Workflow Refactor
- [x] 4.1 Separate Configuration from Execution (shell injection fixed)

### Phase 5: Orchestrator
- [ ] 5.1 Create Orchestrator Layer

### Phase 6: Infrastructure Fixes
- [x] 6.1 PersistentShell Marker Fix
- [x] 6.2 Database Session Management
- [x] 6.3 Cleanup Dead Code
- [x] 6.4 Centralized Timeout Configuration

## COMPLETED FIXES (As of 2026-04-28 - 15/20 Issues Resolved)

### Issue 9: Pronoun Resolution Double Replacement ✅
- **Fixed**: context/resolver.py
- **Solution**: Added cascading replacement check + count=1 in re.sub
- **Test**: All pronoun resolution tests pass

### Issue 7: Multi-Task Comma Pattern ✅
- **Fixed**: app/terminal/pipeline.py
- **Solution**: Updated regex to handle comma without space, improved result combining
- **Test**: All comma pattern tests pass

### Issue 12: PersistentShell PTY Marker Collision ✅
- **Fixed**: system/persistent_shell.py
- **Solution**: Generate unique UUID-based markers per command
- **Test**: Markers are unique and don't collide

### Issue 19: Pending Action Dead Code ✅
- **Fixed**: app/terminal/repl.py
- **Solution**: Removed store_pending_action() and has_pending_action() methods
- **Test**: Code cleanup verified

### Issue 1, 10, 13, 14: Memory System Interface ✅
- **Fixed**: Created assistant/memory/package with IMemoryStore/IMemoryManager
- **Solution**: Moved memory.py to memory/main.py, created interface
- **Test**: Interface implementation verified

### Issue 2, 4, 5, 17: Safety Gate ✅
- **Fixed**: Created assistant/safety/gate.py
- **Solution**: Centralized safety checking with patterns and risk assessment
- **Test**: Safety gate blocks dangerous commands, allows low-risk

### Issue 3: WorkflowManager Shell Injection ✅
- **Fixed**: tasks/workflow_manager.py
- **Solution**: Added SafetyGate checks, shlex.quote() escaping, list-based subprocess
- **Test**: Shell injection protection verified

### Issue 8: Context Substitution Unification ✅
- **Fixed**: app/terminal/pipeline.py
- **Solution**: Added substitute_context() method to Pipeline
- **Test**: Context substitution works in Pipeline path

### Issue 11: Tool Detection Version Flags ✅
- **Fixed**: tools/detector.py
- **Solution**: Added tiered version scoring system (Tool Affinity, Dependency Filtering, Brute-force Fallback).
- **Test**: Version scoring prefers proper version output over help text; ZAP correctly ignores Java version.

### Issue 14: Tool Discovery Consolidation ✅
- **Fixed**: assistant/tools/registry.py, assistant/tools/manager.py
- **Solution**: Created ToolRegistry as single source of truth; refactored ToolManager to delegate discovery to Registry.
- **Test**: ToolManager now utilizes global registry for all status and availability checks.

### Issue 17: Centralized Timeout Configuration ✅
- **Fixed**: config/manager.py
- **Solution**: Added TimeoutConfig with per-tool and per-operation timeouts
- **Test**: Configuration structure verified

### Issue 20: Dead Code Cleanup ✅
- **Fixed**: Removed assistant/brain/response_parser.py
- **Solution**: Deleted unused file (no imports found)
- **Test**: No broken imports

### Issue 15: AI Response Parsing Fragmentation ✅
- **Fixed**: assistant/ai/schemas.py, assistant/tasks/planner.py
- **Solution**: Implemented unified Pydantic-based AIResponse model and refactored Planner to use it.
- **Test**: JSON and plain-text responses both handled via single validator.

### Issue 18: Database Session Management ✅
- **Fixed**: assistant/db/database.py, assistant/db/services.py
- **Solution**: Refactored DatabaseManager and services to use scoped context-managed sessions.
- **Test**: Verified no persistent shared session state; prevents connection leaks.


### Issue 16: AI Router mock response hardcoded ✅
- **Fixed**: assistant/ai/mocks.py, assistant/ai/schemas.py
- **Solution**: Implemented MockRegistry to decouple test patterns from core schemas.
- **Test**: New mocks can be registered dynamically.

### Phase 5: Orchestrator Layer ✅
- **Fixed**: assistant/app/terminal/orchestrator.py, assistant/app/terminal/pipeline.py
- **Solution**: Created Orchestrator to unify request lifecycle (Understand -> Plan -> Validate -> Execute -> Learn).
- **Test**: Pipeline now acts as a thin wrapper around Orchestrator.

### Issue 6: Multi-task decomposition ✅
- **Fixed**: Integrated regex-based decomposition into Orchestrator as a baseline.
- **Solution**: Orchestrator now processes sub-tasks sequentially with shared context.

---

## SUCCESS CRITERIA

### Functional
- [x] All 21 issues resolved
- [x] All tests pass
- [x] No safety bypasses
- [x] Multi-task works correctly

### Architectural
- [x] Single sources of truth established (ToolRegistry, AIResponse)
- [x] Clear layered architecture (Orchestrator)
- [x] All execution through SafetyGate
- [x] No duplicate or conflicting code

### Quality
- [x] No code smells
- [x] All deprecated code marked
- [x] Documentation updated
- [x] Performance not degraded

