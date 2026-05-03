# Layered Memory Architecture Implementation Plan

## Executive Summary

Implement production-grade layered memory system (L0-L4) with multiple storage backends, comprehensive security, and intelligent data flows. Replace current single-layer approach with progressive abstraction.

## Architecture Overview

```
L4: STRATEGY MEMORY      L3: WORKFLOW MEMORY      L2: KNOWLEDGE UNITS
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│ Decision Support     │    │ Procedural Memory   │    │ Semantic Knowledge   │
│ Graph DB + Vector   │    │ Graph + Timeline     │    │ Vector DB + SQL     │
│ Neo4j + Weaviate  │    │ Neo4j + SQLite     │    │ Weaviate + PG       │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
        ↓                           ↓                           ↓
┌───────────────────────────────────────────────────────────────────────┐
│                    L1: PARSED FACTS                          │
│ Structured Fact Store                                           │
│ SQLite + Bleve + Redis                                          │
└───────────────────────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────────────────────┐
│                    L0: RAW EVIDENCE                          │
│ Immutable Evidence Store                                         │
│ Encrypted Files + Metadata DB                                    │
└───────────────────────────────────────────────────────────────────────┘
```

## Phase 1: Core Infrastructure (Week 1-2)

### 1.1 Unified Memory API
**File**: `assistant/memory/layered_api.py`
**Priority**: Critical

**Interfaces**:
```python
class LayeredMemoryAPI:
    """Unified interface for all memory layers."""
    
    # Evidence layer (L0)
    def store_evidence(evidence: EvidenceData) -> str
    def get_evidence(evidence_id: str) -> Optional[EvidenceData]
    def search_evidence(query: EvidenceQuery) -> List[EvidenceData]
    
    # Facts layer (L1)
    def add_fact(fact: FactData) -> str
    def get_fact(fact_id: str) -> Optional[FactData]
    def search_facts(query: FactQuery) -> List[FactData]
    def relate_facts(from_id: str, to_id: str, relationship_type: str)
    
    # Knowledge layer (L2)
    def add_knowledge(knowledge: KnowledgeUnit) -> str
    def get_knowledge(knowledge_id: str) -> Optional[KnowledgeUnit]
    def search_knowledge(query: KnowledgeQuery) -> List[KnowledgeUnit]
    def validate_knowledge(knowledge_id: str, valid: bool)
    def semantic_search(query: str, limit: int = 10) -> List[KnowledgeUnit]
    
    # Workflow layer (L3)
    def add_workflow(workflow: WorkflowData) -> str
    def get_workflow(workflow_id: str) -> Optional[WorkflowData]
    def search_workflows(query: WorkflowQuery) -> List[WorkflowData]
    def execute_workflow(workflow_id: str, context: dict) -> WorkflowExecution
    
    # Strategy layer (L4)
    def add_strategy(strategy: StrategyData) -> str
    def get_strategy(strategy_id: str) -> Optional[StrategyData]
    def search_strategies(query: StrategyQuery) -> List[StrategyData]
    def apply_strategy(strategy_id: str, context: dict) -> StrategyApplication
```

### 1.2 Configuration Management
**File**: `assistant/config/memory_config.py`
**Priority**: High

```python
MEMORY_CONFIG = {
    "backends": {
        "evidence": {
            "type": "file+sqlite",
            "path": "~/.assistant/evidence/",
            "encryption": "ChaCha20-Poly1305"
        },
        "facts": {
            "type": "sqlite",
            "path": "~/.assistant/facts.db",
            "fuzzy_index": "bleve"
        },
        "knowledge": {
            "type": "vector+sql",
            "vector_db": "weaviate",
            "sql_db": "postgresql",
            "embedding_model": "all-MiniLM-L6-v2"
        },
        "workflows": {
            "type": "graph+sqlite",
            "graph_db": "neo4j",
            "timeline_db": "sqlite"
        },
        "strategies": {
            "type": "graph+vector",
            "graph_db": "neo4j",
            "vector_db": "weaviate"
        }
    },
    "security": {
        "encryption_at_rest": True,
        "secret_redaction": True,
        "workspace_isolation": True,
        "integrity_checks": True
    },
    "caching": {
        "enabled": True,
        "session_cache": True,
        "tool_cache": True,
        "hot_memory": True
    }
}
```

## Phase 2: Evidence Layer Implementation (Week 2-3)

### 2.1 Evidence Storage Engine
**File**: `assistant/memory/evidence_layer.py`
**Priority**: High

**Components**:
```python
class EvidenceStorage:
    """Immutable raw evidence storage."""
    
    def store_raw(self, evidence: dict) -> str:
        """Store evidence with encryption and integrity."""
        evidence_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Encrypt content based on sensitivity
        ciphertext, key_id = encryption_manager.encrypt(content)
        
        # Store to immutable location
        file_path = f"{evidence_dir}/{evidence_id}.enc"
        with open(file_path, 'wb') as f:
            f.write(ciphertext)
        
        # Store metadata
        metadata = {
            "evidence_id": evidence_id,
            "file_path": file_path,
            "file_hash": file_hash,
            "sensitivity": classify_sensitivity(content),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.metadata_db.insert(metadata)
        return evidence_id
    
    def get_evidence(self, evidence_id: str) -> Optional[dict]:
        """Retrieve evidence with decryption and verification."""
        metadata = self.metadata_db.get(evidence_id)
        if not metadata:
            return None
        
        # Verify file integrity
        current_hash = hashlib.sha256(file_path.read()).hexdigest()
        if current_hash != metadata["file_hash"]:
            raise IntegrityError("Evidence file corrupted")
        
        # Decrypt content
        content = encryption_manager.decrypt(file_content, metadata["key_id"])
        return {**metadata, "content": content}
```

### 2.2 Evidence Metadata Schema
**File**: `assistant/db/evidence_schema.py`
**Priority**: High

```sql
-- Evidence metadata database
CREATE TABLE evidence_metadata (
    evidence_id TEXT PRIMARY KEY,
    evidence_type TEXT NOT NULL,
    source_session TEXT,
    workspace_id TEXT NOT NULL,
    target_id TEXT,
    timestamp TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT UNIQUE NOT NULL,
    file_size_bytes INTEGER,
    mime_type TEXT,
    capture_method TEXT,
    content_preview TEXT,
    sensitivity TEXT NOT NULL,
    retention_policy TEXT NOT NULL,
    related_commands TEXT,
    metadata JSON
);

-- Performance indexes
CREATE INDEX idx_evidence_timestamp ON evidence_metadata(timestamp DESC);
CREATE INDEX idx_evidence_workspace ON evidence_metadata(workspace_id);
CREATE INDEX idx_evidence_target ON evidence_metadata(target_id);
CREATE INDEX idx_evidence_type ON evidence_metadata(evidence_type);
CREATE INDEX idx_evidence_session ON evidence_metadata(source_session);
CREATE INDEX idx_evidence_sensitivity ON evidence_metadata(sensitivity);
CREATE INDEX idx_evidence_retention ON evidence_metadata(retention_policy);
```

## Phase 3: Facts Layer Implementation (Week 3-4)

### 3.1 Fact Extraction Engine
**File**: `assistant/memory/fact_extractor.py`
**Priority**: High

**Components**:
```python
class FactExtractor:
    """Extract structured facts from raw evidence."""
    
    def extract_from_evidence(self, evidence_id: str) -> List[FactData]:
        """Parse evidence into structured facts."""
        evidence = evidence_storage.get_evidence(evidence_id)
        
        facts = []
        
        # Extract based on evidence type
        if evidence["evidence_type"] == "terminal_output":
            facts.extend(self._parse_terminal_output(evidence["content"]))
        elif evidence["evidence_type"] == "log":
            facts.extend(self._parse_log_file(evidence["content"]))
        elif evidence["evidence_type"] == "file":
            facts.extend(self._parse_file_content(evidence["content"]))
        
        # Link facts to evidence
        for fact in facts:
            fact.source_evidence_id = evidence_id
        
        return facts
    
    def _parse_terminal_output(self, output: str) -> List[FactData]:
        """Extract facts from terminal output."""
        facts = []
        
        # Extract IPs
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', output)
        for ip in set(ips):
            facts.append(FactData(
                fact_type="ip",
                value=ip,
                confidence=1.0,
                metadata={"ip_version": "ipv4"}
            ))
        
        # Extract domains
        domains = re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.(?:com|net|org|io)\b', output)
        for domain in set(domains):
            facts.append(FactData(
                fact_type="domain",
                value=domain,
                confidence=0.9,
                metadata={"domain_tld": domain.split('.')[-1]}
            ))
        
        # Extract ports
        ports = re.findall(r'\b(?:(\d{1,5})/[a-z]{3,5})\b', output)
        for port in set(ports):
            num, proto = port.split('/')
            facts.append(FactData(
                fact_type="port",
                value=num,
                confidence=1.0,
                metadata={"port_protocol": proto}
            ))
        
        return facts
```

### 3.2 Fact Storage with Relationships
**File**: `assistant/memory/fact_storage.py`
**Priority**: High

**Components**:
```python
class FactStorage:
    """Structured fact storage with relationship support."""
    
    def add_fact(self, fact: FactData) -> str:
        """Store fact with normalization and deduplication."""
        fact_id = str(uuid.uuid4())
        normalized = self._normalize_fact(fact)
        
        # Check for duplicates
        existing = self.fuzzy_index.search(normalized, limit=1)
        if existing and existing["score"] > 0.9:
            # Merge confidence
            self._update_fact_confidence(existing["id"], fact.confidence)
            return existing["id"]
        
        # Store new fact
        self.db.insert({
            "fact_id": fact_id,
            "fact_type": fact.type,
            "value": fact.value,
            "normalized_value": normalized,
            "confidence": fact.confidence,
            "source_evidence_id": fact.source_evidence_id,
            "tags": fact.tags
        })
        
        return fact_id
    
    def relate_facts(self, from_id: str, to_id: str, relationship_type: str):
        """Create relationship between facts."""
        relationship_id = str(uuid.uuid4())
        self.relationships_db.insert({
            "relationship_id": relationship_id,
            "from_fact_id": from_id,
            "to_fact_id": to_id,
            "relationship_type": relationship_type,
            "confidence": 1.0
        })
        return relationship_id
```

## Phase 4: Knowledge Layer Implementation (Week 4-5)

### 4.1 Knowledge Generation Engine
**File**: `assistant/memory/knowledge_generator.py`
**Priority**: High

**Components**:
```python
class KnowledgeGenerator:
    """Generate validated knowledge from facts."""
    
    def generate_from_facts(self, facts: List[FactData]) -> List[KnowledgeUnit]:
        """Transform facts into reusable knowledge."""
        knowledge_units = []
        
        # Group related facts
        fact_groups = self._group_related_facts(facts)
        
        for group in fact_groups:
            # Generate knowledge unit
            content = self._synthesize_content(group)
            embedding = self.embedding_model.embed(content)
            
            knowledge = KnowledgeUnit(
                knowledge_type="reusable_fact",
                content=content,
                confidence=self._calculate_confidence(group),
                source_facts=[f.fact_id for f in group],
                embedding_vector=embedding,
                validation_status="pending"
            )
            
            knowledge_units.append(knowledge)
        
        return knowledge_units
    
    def _calculate_confidence(self, facts: List[FactData]) -> float:
        """Calculate confidence for knowledge based on source facts."""
        if not facts:
            return 0.0
        
        # Weight by fact confidence and count
        total_confidence = sum(f.confidence for f in facts)
        return min(total_confidence / len(facts), 1.0)
```

### 4.2 Semantic Search Integration
**File**: `assistant/memory/semantic_search.py`
**Priority**: High

**Components**:
```python
class SemanticSearch:
    """Semantic search across knowledge units."""
    
    def search(self, query: str, limit: int = 10) -> List[KnowledgeUnit]:
        """Perform semantic search using vector embeddings."""
        # Generate query embedding
        query_embedding = self.embedding_model.embed(query)
        
        # Search vector database
        results = self.vector_db.search(
            query_vector=query_embedding,
            limit=limit,
            metric="cosine"
        )
        
        # Filter by workspace and access
        filtered = [
            r for r in results
            if self._has_access(r)
        ]
        
        return filtered
    
    def _has_access(self, knowledge: KnowledgeUnit) -> bool:
        """Check workspace access permissions."""
        return (
            knowledge.workspace_id == self.current_workspace or
            knowledge.sensitivity == "public"
        )
```

## Phase 5: Workflow Layer Implementation (Week 5-6)

### 5.1 Workflow Storage Engine
**File**: `assistant/memory/workflow_storage.py`
**Priority**: High

**Components**:
```python
class WorkflowStorage:
    """Store and retrieve procedural workflows."""
    
    def add_workflow(self, workflow: WorkflowData) -> str:
        """Store workflow with step sequence."""
        workflow_id = str(uuid.uuid4())
        
        # Store in graph database
        self.graph_db.create_node("Workflow", {
            "workflow_id": workflow_id,
            "workflow_type": workflow.type,
            "title": workflow.title,
            "success_rate": workflow.success_rate,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Store steps as related nodes
        for step in workflow.steps:
            step_id = str(uuid.uuid4())
            self.graph_db.create_node("Step", {
                "step_id": step_id,
                "step_order": step.order,
                "command": step.command,
                "tool": step.tool
            })
            
            # Link workflow to step
            self.graph_db.create_relationship(
                workflow_id, step_id, "HAS_STEP", {"step_order": step.order}
            )
        
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowData]:
        """Retrieve complete workflow with steps."""
        workflow_node = self.graph_db.get_node(workflow_id)
        if not workflow_node:
            return None
        
        # Get all steps
        steps = self.graph_db.get_related_nodes(workflow_id, "HAS_STEP")
        ordered_steps = sorted(steps, key=lambda s: s["step_order"])
        
        return WorkflowData(**workflow_node, steps=ordered_steps)
```

### 5.2 Workflow Pattern Matching
**File**: `assistant/memory/workflow_matcher.py`
**Priority**: Medium

**Components**:
```python
class WorkflowMatcher:
    """Match and recommend workflows based on context."""
    
    def find_matching_workflows(self, context: dict) -> List[WorkflowData]:
        """Find workflows relevant to current context."""
        query = self._build_search_query(context)
        
        # Semantic search for workflows
        semantic_results = self.semantic_search.search(query, limit=5)
        
        # Pattern matching for workflows
        pattern_results = self._pattern_search(context)
        
        # Combine and rank results
        combined = self._rank_and_combine(semantic_results, pattern_results)
        return combined[:5]
    
    def _pattern_search(self, context: dict) -> List[WorkflowData]:
        """Find workflows matching current patterns."""
        current_patterns = self._extract_patterns(context)
        
        # Match against stored workflow patterns
        matches = []
        for workflow in self.workflow_storage.get_all():
            workflow_patterns = self._extract_patterns_from_workflow(workflow)
            similarity = self._pattern_similarity(current_patterns, workflow_patterns)
            
            if similarity > 0.7:
                matches.append((workflow, similarity))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
```

## Phase 6: Strategy Layer Implementation (Week 6-7)

### 6.1 Strategy Storage Engine
**File**: `assistant/memory/strategy_storage.py`
**Priority**: High

**Components**:
```python
class StrategyStorage:
    """Store high-level strategic knowledge."""
    
    def add_strategy(self, strategy: StrategyData) -> str:
        """Store strategy with rules and relationships."""
        strategy_id = str(uuid.uuid4())
        
        # Store in graph database
        self.graph_db.create_node("Strategy", {
            "strategy_id": strategy_id,
            "strategy_type": strategy.type,
            "title": strategy.title,
            "domain": strategy.domain,
            "confidence": strategy.confidence,
            "application_count": 0
        })
        
        # Store rules
        for rule in strategy.rules:
            rule_id = str(uuid.uuid4())
            self.graph_db.create_node("Rule", {
                "rule_id": rule_id,
                "condition": rule.condition,
                "action": rule.action,
                "priority": rule.priority,
                "success_rate": 0.0
            })
            
            # Link strategy to rule
            self.graph_db.create_relationship(strategy_id, rule_id, "HAS_RULE")
        
        return strategy_id
```

### 6.2 Strategy Application Engine
**File**: `assistant/memory/strategy_engine.py`
**Priority**: High

**Components**:
```python
class StrategyEngine:
    """Apply strategies to make decisions."""
    
    def apply_strategy(self, strategy_id: str, context: dict) -> StrategyApplication:
        """Execute strategy against current context."""
        strategy = self.strategy_storage.get_strategy(strategy_id)
        if not strategy:
            return StrategyApplication(success=False, error="Strategy not found")
        
        # Evaluate conditions
        matching_rules = self._evaluate_rules(strategy.rules, context)
        
        if not matching_rules:
            return StrategyApplication(
                success=True,
                recommendation="Strategy applied successfully",
                confidence=strategy.confidence,
                actions=[]
            )
        
        # Execute matching actions
        actions = []
        for rule in matching_rules:
            result = self._execute_rule(rule.action, context)
            actions.append(result)
            self._track_rule_success(rule.rule_id, result.success)
        
        return StrategyApplication(
            success=True,
            recommendation="Applied {} rules".format(len(matching_rules)),
            confidence=strategy.confidence,
            actions=actions
        )
    
    def _evaluate_rules(self, rules: List[Rule], context: dict) -> List[Rule]:
        """Find rules that match current context."""
        matching = []
        for rule in rules:
            if self._condition_matches(rule.condition, context):
                matching.append(rule)
        return matching
```

## Phase 7: Integration & Testing (Week 8)

### 7.1 Cross-Layer Data Flow
**File**: `assistant/memory/data_flow.py`
**Priority**: Critical

**Components**:
```python
class DataFlowManager:
    """Orchestrate data flow across all layers."""
    
    def process_evidence(self, raw_data: dict) -> str:
        """Complete evidence processing pipeline."""
        # L0: Store raw evidence
        evidence_id = self.evidence_layer.store_raw(raw_data)
        
        # L1: Extract and store facts
        facts = self.fact_extractor.extract_from_evidence(evidence_id)
        for fact in facts:
            self.fact_layer.add_fact(fact)
        
        # L2: Generate and store knowledge
        knowledge = self.knowledge_generator.generate_from_facts(facts)
        for unit in knowledge:
            self.knowledge_layer.add_knowledge(unit)
        
        # L3: Detect and store workflows
        workflows = self.workflow_detector.detect_patterns(facts, knowledge)
        for workflow in workflows:
            self.workflow_layer.add_workflow(workflow)
        
        # L4: Generate and store strategies
        strategies = self.strategy_generator.generate_from_workflows(workflows)
        for strategy in strategies:
            self.strategy_layer.add_strategy(strategy)
        
        return evidence_id
    
    def unified_query(self, query: str) -> dict:
        """Query all layers and combine results."""
        # L4: Get strategic guidance
        strategies = self.strategy_layer.search_strategies(query)
        
        # L3: Get relevant workflows
        workflows = self.workflow_layer.search_workflows(query, strategies)
        
        # L2: Get supporting knowledge
        knowledge = self.knowledge_layer.search_knowledge(query)
        
        # L1: Get raw evidence if needed
        evidence = self.evidence_layer.search_evidence(query)
        
        # L1: Get specific facts
        facts = self.fact_layer.search_facts(query)
        
        return {
            "strategies": strategies,
            "workflows": workflows,
            "knowledge": knowledge,
            "evidence": evidence,
            "facts": facts
        }
```

### 7.2 Comprehensive Testing
**File**: `tests/memory/test_layered_system.py`
**Priority**: High

**Test Suites**:
```python
# Evidence layer tests
def test_evidence_storage():
    """Test immutable evidence storage."""
    evidence_id = evidence_storage.store_raw(test_evidence)
    retrieved = evidence_storage.get_evidence(evidence_id)
    assert retrieved.content == test_evidence.content
    assert retrieved.file_hash == test_evidence.file_hash

# Facts layer tests
def test_fact_extraction():
    """Test fact extraction from evidence."""
    facts = fact_extractor.extract_from_evidence(evidence_id)
    assert all(f.confidence > 0.0 for f in facts)
    assert len(facts) > 0

# Knowledge layer tests
def test_semantic_search():
    """Test semantic search functionality."""
    results = semantic_search.search("web vulnerability", limit=5)
    assert len(results) > 0
    assert all(k.workspace_id == current_workspace for k in results)

# Workflow layer tests
def test_workflow_matching():
    """Test workflow pattern matching."""
    matches = workflow_matcher.find_matching_workflows(context)
    assert len(matches) > 0
    assert all(m.success_rate > 0.5 for m in matches)

# Cross-layer integration tests
def test_data_flow():
    """Test complete data flow pipeline."""
    result = data_flow.process_evidence(test_evidence)
    assert result["evidence"] is not None
    assert len(result["facts"]) > 0
    assert len(result["knowledge"]) > 0

# Performance tests
def test_query_performance():
    """Test query latency across layers."""
    start = time.time()
    result = data_flow.unified_query("reconnaissance workflow")
    duration = time.time() - start
    assert duration < 1.0  # 1 second for complex query
```

## Phase 8: Migration & Deployment (Week 8-9)

### 8.1 Legacy Data Migration
**File**: `assistant/memory/migration.py`
**Priority**: Critical

**Components**:
```python
class LegacyMigrator:
    """Migrate existing data to layered system."""
    
    def migrate_from_old_system(self, old_db_path: str):
        """Migrate single-layer data to multi-layer system."""
        # Step 1: Migrate entities to L2 knowledge
        old_entities = self._load_old_entities(old_db_path)
        for entity in old_entities:
            knowledge_unit = self._entity_to_knowledge(entity)
            self.knowledge_layer.add_knowledge(knowledge_unit)
        
        # Step 2: Migrate conversations to L3 workflows
        old_conversations = self._load_old_conversations(old_db_path)
        for conv in old_conversations:
            workflow = self._conversation_to_workflow(conv)
            self.workflow_layer.add_workflow(workflow)
        
        # Step 3: Migrate snapshots to L0 evidence
        old_snapshots = self._load_old_snapshots(old_db_path)
        for snapshot in old_snapshots:
            evidence = self._snapshot_to_evidence(snapshot)
            self.evidence_layer.store_raw(evidence)
```

### 8.2 Deployment Checklist
**File**: `assistant/memory/deployment.py`
**Priority**: Critical

```python
DEPLOYMENT_CHECKLIST = {
    "infrastructure": [
        "All storage backends installed",
        "Vector database configured",
        "Graph database accessible",
        "Encryption keys generated",
        "Workspace isolation tested"
    ],
    "data": [
        "Legacy data migrated",
        "All indexes built",
        "Caches configured",
        "Security policies enforced"
    ],
    "testing": [
        "All unit tests passing",
        "Integration tests completed",
        "Performance benchmarks met",
        "Security audit passed"
    ],
    "monitoring": [
        "Logging configured",
        "Metrics collection enabled",
        "Alert thresholds set",
        "Health checks scheduled"
    ]
}
```

## Security Implementation

### Multi-Layer Encryption
```python
ENCRYPTION_LAYERS = {
    "L0_EVIDENCE": {
        "algorithm": "ChaCha20-Poly1305",
        "scope": "file_level",
        "key_rotation": "90_days",
        "integrity": "SHA-256"
    },
    "L1_FACTS": {
        "algorithm": "AES-256-GCM",
        "scope": "field_level",
        "key_rotation": "90_days",
        "integrity": "relationship_consistency"
    },
    "L2_KNOWLEDGE": {
        "algorithm": "ChaCha20-Poly1305",
        "scope": "content_level",
        "key_rotation": "90_days",
        "integrity": "hash_verification"
    },
    "L3_WORKFLOWS": {
        "algorithm": "AES-256-GCM",
        "scope": "structure_level",
        "key_rotation": "90_days",
        "integrity": "step_sequence_validation"
    },
    "L4_STRATEGIES": {
        "algorithm": "ChaCha20-Poly1305",
        "scope": "content_level",
        "key_rotation": "90_days",
        "integrity": "rule_consistency"
    }
}
```

### Workspace Isolation Enforcement
```python
WORKSPACE_ISOLATION = {
    "L0": "Complete isolation (no cross-workspace evidence access)",
    "L1": "Workspace-scoped queries (no cross-workspace entity resolution)",
    "L2": "Workspace-restricted knowledge (no cross-workspace semantic search)",
    "L3": "Workspace-specific workflows (no cross-workflow pattern sharing)",
    "L4": "Global strategies only (can share high-level lessons)"
}
```

### Secret Redaction at Layer Boundaries
```python
SECRET_REDACTION_BOUNDERIES = {
    "L0→L1": "Secret patterns redacted before fact extraction",
    "L1→L2": "Sensitive fields encrypted before knowledge generation",
    "L2→L3": "Security info filtered before workflow composition",
    "L3→L4": "Tactical lessons only (no operational secrets)",
    "All layers": "User approval for cross-layer secret access"
}
```

## Performance Targets

### Query Performance
```python
PERFORMANCE_TARGETS = {
    "L0_evidence_query": "< 50ms",
    "L1_fact_search": "< 100ms",
    "L2_knowledge_search": "< 200ms",
    "L3_workflow_search": "< 300ms",
    "L4_strategy_search": "< 100ms",
    "cross_layer_query": "< 500ms",
    "semantic_search": "< 200ms"
}
```

### Storage Performance
```python
STORAGE_TARGETS = {
    "evidence_storage": "100MB/day",
    "fact_insertion": "1000 facts/sec",
    "knowledge_insertion": "100 units/sec",
    "workflow_insertion": "10 workflows/sec",
    "strategy_insertion": "5 strategies/sec",
    "cache_hit_rate": "> 80%"
}
```

## Success Criteria

### Functional Requirements
- [ ] All 5 layers implemented with dedicated storage
- [ ] Cross-layer data flow operational
- [ ] Workspace isolation enforced at all levels
- [ ] Security model applied (encryption + access control)
- [ ] Semantic search functional for knowledge layer
- [ ] Pattern matching functional for workflow layer
- [ ] Strategy engine operational
- [ ] Legacy data migration completed
- [ ] All caching layers functional

### Non-Functional Requirements
- [ ] Query performance meets targets
- [ ] Storage performance meets targets
- [ ] Cache hit rates above 80%
- [ ] Zero data loss during migration
- [ ] Security audit passed
- [ ] Scalability to 10TB evidence storage
- [ ] Support for concurrent access
- [ ] Automated backup and recovery

### Quality Requirements
- [ ] Unit test coverage > 90%
- [ ] Integration test coverage > 80%
- [ ] Security penetration testing completed
- [ ] Performance benchmarking completed
- [ ] Documentation complete
- [ ] Code review completed
- [ ] Monitoring and alerting configured

## Timeline

### Implementation Phases
- **Phase 1**: Week 1-2 - Core infrastructure (API + config)
- **Phase 2**: Week 2-3 - Evidence layer (storage + metadata)
- **Phase 3**: Week 3-4 - Facts layer (extraction + storage)
- **Phase 4**: Week 4-5 - Knowledge layer (generation + search)
- **Phase 5**: Week 5-6 - Workflow layer (storage + patterns)
- **Phase 6**: Week 6-7 - Strategy layer (storage + engine)
- **Phase 7**: Week 8 - Integration + testing
- **Phase 8**: Week 8-9 - Migration + deployment

### Milestones
- **Week 2**: Core API functional
- **Week 3**: Evidence layer operational
- **Week 4**: Facts layer operational
- **Week 5**: Knowledge layer operational
- **Week 6**: Workflow layer operational
- **Week 7**: Strategy layer operational
- **Week 8**: All layers integrated
- **Week 9**: Legacy data migrated, production ready

## Conclusion

This layered memory architecture provides comprehensive, secure, and performant memory system for AI assistant. Progressive abstraction from raw evidence to strategic intelligence enables both precise fact retrieval and high-level decision support.

**Next Steps**: Begin Phase 1 implementation with focus on core infrastructure and unified API.

**Estimated Total Duration**: 9 weeks
**Team Required**: 2-3 developers (backend + integration)
**Key Dependencies**: Vector database, graph database, encryption library
**Success Metrics**: Query latency <500ms, cache hit rate >80%, security audit passed