# Retrieval, Learning & Verification System - Implementation Plan

## Executive Summary

Complete design of retrieval, learning, and verification system for AI assistant using layered memory architecture (L0-L4). Provides intelligent context building, automatic learning, and comprehensive quality control.

## System Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │  AI AGENT ORCHESTRATOR                  │
                    │  - Decides what enters prompt           │
                    │  - Manages memory interactions              │
                    │  - Oversees learning & verification      │
                    └─────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────────────────┐
        │            RETRIEVAL & CONTEXT BUILDER                  │
        │  - Multi-modal retrieval engine                                │
        │  - Intelligent context assembly                                │
        │  - Source attribution & citation                                 │
        └───────────────────────────────────────────────────────────────────┘
                    ↓
        ┌───────────────────────────────────────────────────────────────────┐
        │                LAYERED MEMORY SYSTEM (L0-L4)                 │
        │  - Evidence → Facts → Knowledge → Workflows → Strategies     │
        │  - Multi-backend storage + semantic indexing                    │
        │  - Workspace isolation + security enforcement                     │
        └───────────────────────────────────────────────────────────────────┘
                    ↑
        ┌───────────────────────────────────────────────────────────────────┐
        │              LEARNING & PROMOTION ENGINE                     │
        │  - Automatic pattern detection                                   │
        │  - Confidence score updates                                      │
        │  - Layer promotion logic                                        │
        │  - Workflow synthesis                                            │
        └───────────────────────────────────────────────────────────────────┘
                    ↑
        ┌───────────────────────────────────────────────────────────────────┐
        │               VERIFICATION ENGINE                          │
        │  - Quality scoring                                             │
        │  - Contradiction detection                                     │
        │  - Hallucination prevention                                    │
        │  - Unsafe memory rejection                                      │
        └───────────────────────────────────────────────────────────────────┘
```

## 1. RETRIEVAL DESIGN

### Multi-Modal Retrieval Engine

**File**: `assistant/retrieval/retrieval_engine.py`

```python
class RetrievalEngine:
    """Multi-modal retrieval across all memory layers."""
    
    def __init__(self):
        self.keyword_searcher = KeywordSearcher()
        self.semantic_searcher = SemanticSearcher()
        self.graph_searcher = GraphSearcher()
        self.ranker = RelevanceRanker()
        self.filterer = QueryFilterer()
    
    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Multi-modal retrieval with intelligent ranking."""
        # 1. Parse and classify query
        parsed_query = self._parse_query(query)
        
        # 2. Execute parallel searches
        results = {
            "keyword": self.keyword_searcher.search(parsed_query),
            "semantic": self.semantic_searcher.search(parsed_query),
            "graph": self.graph_searcher.search(parsed_query),
            "structured": self.filterer.search(parsed_query)
        }
        
        # 3. Merge and rank results
        merged = self._merge_results(results)
        ranked = self.ranker.rank(merged, parsed_query)
        
        # 4. Apply filters and limits
        filtered = self.filterer.apply_filters(ranked, parsed_query)
        limited = self._apply_limits(filtered, parsed_query)
        
        return RetrievalResult(
            query=parsed_query,
            results=limited,
            sources=[r.source_layer for r in limited],
            confidence=sum(r.confidence for r in limited) / len(limited),
            execution_time_ms=time.time() - start_time
        )
```

### Retrieval Components

#### 1. Keyword Searcher
```python
class KeywordSearcher:
    """Exact and fuzzy keyword matching."""
    
    def search(self, query: ParsedQuery) -> List[RetrievalResult]:
        """Search using keyword matching with fuzziness."""
        results = []
        
        # L1: Search facts (normalized values)
        for fact in self.fact_layer.search_exact(query.keywords):
            results.append(RetrievalResult(
                content=fact.value,
                layer="L1",
                source_id=fact.fact_id,
                confidence=fact.confidence,
                match_type="exact"
            ))
        
        # L2: Search knowledge (semantic-aware keywords)
        for unit in self.knowledge_layer.search_by_keywords(query.keywords):
            results.append(RetrievalResult(
                content=unit.content,
                layer="L2",
                source_id=unit.knowledge_id,
                confidence=unit.confidence,
                match_type="semantic_keyword"
            ))
        
        # Add fuzzy matches (Levenshtein < 3)
        fuzzy = self._fuzzy_search(query.keywords, results)
        results.extend(fuzzy)
        
        return results
```

#### 2. Semantic Searcher  
```python
class SemanticSearcher:
    """Vector-based semantic search."""
    
    def search(self, query: ParsedQuery) -> List[RetrievalResult]:
        """Semantic search using vector embeddings."""
        # Generate query embedding
        query_embedding = self.embedding_model.embed(query.normalized_text)
        
        # Search L2 knowledge by vector similarity
        results = []
        vector_results = self.vector_db.search(
            query_vector=query_embedding,
            limit=query.semantic_limit * 2,  # Get extra for re-ranking
            metric="cosine"
        )
        
        # Convert to retrieval results
        for vr in vector_results:
            knowledge_unit = self.knowledge_layer.get_knowledge(vr.knowledge_id)
            results.append(RetrievalResult(
                content=knowledge_unit.content,
                layer="L2",
                source_id=knowledge_unit.knowledge_id,
                confidence=knowledge_unit.confidence * vr.similarity,
                match_type="semantic",
                semantic_similarity=vr.similarity
            ))
        
        return results
```

#### 3. Graph Searcher
```python
class GraphSearcher:
    """Relationship-based search in workflow and strategy layers."""
    
    def search(self, query: ParsedQuery) -> List[RetrievalResult]:
        """Search using graph relationships."""
        results = []
        
        # L3: Search workflows by concept matching
        workflow_results = self.graph_db.query(
            """
            MATCH (w:Workflow)-[:RELATED_TO*]->(s:Strategy)
            WHERE any(keyword IN s.title) OR 
                  any(keyword IN s.description)
            RETURN w, s, 
                   gds.similarity(w.description, $query_text) AS sim
            ORDER BY sim DESC
            LIMIT ?workflow_limit
            """,
            query_text=query.normalized_text,
            workflow_limit=query.workflow_limit
        )
        
        for workflow in workflow_results:
            results.append(RetrievalResult(
                content=workflow.description,
                layer="L3",
                source_id=workflow.workflow_id,
                confidence=workflow.success_rate,
                match_type="graph_relationship",
                graph_distance=workflow.graph_distance
            ))
        
        # L4: Search strategies by domain matching
        strategy_results = self.graph_db.query(
            """
            MATCH (s:Strategy)
            WHERE s.domain IN $domains OR 
                  any(keyword IN s.title)
            RETURN s
            ORDER BY s.success_rate DESC
            LIMIT ?strategy_limit
            """,
            domains=query.domains,
            strategy_limit=query.strategy_limit
        )
        
        for strategy in strategy_results:
            results.append(RetrievalResult(
                content=strategy.description,
                layer="L4",
                source_id=strategy.strategy_id,
                confidence=strategy.application_count * strategy.success_rate,
                match_type="domain_match"
            ))
        
        return results
```

#### 4. Query Filterer
```python
class QueryFilterer:
    """Structured filtering and workspace/target isolation."""
    
    def search(self, query: ParsedQuery) -> List[RetrievalResult]:
        """Search using structured filters."""
        results = []
        
        # Apply workspace filter
        if query.workspace_id:
            workspace_results = self._filter_by_workspace(query.workspace_id)
            results.extend(workspace_results)
        
        # Apply target filter
        if query.target_id:
            target_results = self._filter_by_target(query.target_id)
            results.extend(target_results)
        
        # Apply sensitivity filter
        if query.min_sensitivity:
            sensitivity_results = self._filter_by_sensitivity(query.min_sensitivity)
            results.extend(sensitivity_results)
        
        # Apply date range filter
        if query.date_range:
            date_results = self._filter_by_date(query.date_range)
            results.extend(date_results)
        
        return results
    
    def apply_filters(self, results: List[RetrievalResult], query: ParsedQuery) -> List[RetrievalResult]:
        """Post-retrieval filtering."""
        filtered = results
        
        # Filter by confidence threshold
        if query.min_confidence:
            filtered = [r for r in filtered if r.confidence >= query.min_confidence]
        
        # Filter by recency
        if query.max_age_days:
            cutoff = datetime.now() - timedelta(days=query.max_age_days)
            filtered = [r for r in filtered if r.last_accessed > cutoff]
        
        # Filter by layer preferences
        if query.preferred_layers:
            filtered = [r for r in filtered if r.layer in query.preferred_layers]
        
        return filtered
```

#### 5. Relevance Ranker
```python
class RelevanceRanker:
    """Intelligent ranking algorithm for retrieval results."""
    
    def rank(self, results: List[RetrievalResult], query: ParsedQuery) -> List[RetrievalResult]:
        """Rank results by multi-factor relevance scoring."""
        # Calculate relevance scores
        scored_results = []
        
        for result in results:
            score = self._calculate_relevance(result, query)
            result.relevance_score = score
            scored_results.append(result)
        
        # Sort by score
        ranked = sorted(scored_results, key=lambda r: r.relevance_score, reverse=True)
        return ranked
    
    def _calculate_relevance(self, result: RetrievalResult, query: ParsedQuery) -> float:
        """Calculate multi-factor relevance score."""
        score = 0.0
        
        # 1. Text similarity (0-35%)
        text_similarity = self._text_similarity(result.content, query.normalized_text)
        score += 0.35 * text_similarity
        
        # 2. Semantic match (0-25%)
        if result.match_type == "semantic":
            score += 0.25 * result.semantic_similarity
        
        # 3. Graph proximity (0-15%)
        if result.match_type == "graph_relationship":
            graph_bonus = 1.0 / (result.graph_distance + 1)
            score += 0.15 * graph_bonus
        
        # 4. Confidence (0-15%)
        score += 0.15 * result.confidence
        
        # 5. Recency bonus (0-10%)
        days_old = (datetime.now() - result.last_accessed).days
        recency_bonus = max(0, (90 - days_old) / 90)
        score += 0.10 * recency_bonus
        
        return min(score, 1.0)  # Cap at 1.0
```

## 2. CONTEXT BUILDER

### Intelligent Context Assembly

**File**: `assistant/context/context_builder.py`

```python
class ContextBuilder:
    """Builds optimal AI prompt context from retrieved memory."""
    
    def __init__(self):
        self.max_context_tokens = 4000  # ~3K tokens for context
        self.evidence_limit = 10  # Max evidence items
        self.fact_limit = 20  # Max fact items
        self.knowledge_limit = 15  # Max knowledge units
        self.workspace_threshold = 0.3  # 30% workspace items
        self.source_required = True  # Always cite sources
    
    def build_context(self, query: str, retrieval_result: RetrievalResult) -> PromptContext:
        """Build structured context from retrieval results."""
        # 1. Categorize results
        categorized = self._categorize_results(retrieval_result.results)
        
        # 2. Prevent context flooding
        filtered = self._prevent_flooding(categorized, query)
        
        # 3. Summarize if needed
        summarized = self._summarize_if_needed(filtered, query)
        
        # 4. Add source citations
        with_citations = self._add_citations(summarized)
        
        # 5. Separate facts from interpretations
        structured = self._separate_facts_from_guesses(with_citations)
        
        return PromptContext(
            original_query=query,
            filtered_items=filtered.count,
            context=structured["context"],
            evidence=structured["evidence"],
            interpretations=structured["interpretations"],
            confidence=summarized["confidence"],
            sources=with_citations["sources"],
            token_usage=self._estimate_tokens(structured)
        )
```

### Context Assembly Logic

#### 1. Result Categorization
```python
def _categorize_results(self, results: List[RetrievalResult]) -> dict:
    """Categorize retrieval results by type and certainty."""
    categorized = {
        "facts": [],           # High certainty, from L1
        "knowledge": [],       # Medium certainty, from L2
        "workflows": [],       # Procedural, from L3
        "strategies": [],     # Strategic, from L4
        "evidence": [],        # Raw data, from L0
        "guesses": []         # Low certainty interpretations
    }
    
    for result in results:
        if result.layer == "L1" and result.confidence >= 0.9:
            categorized["facts"].append(result)
        elif result.layer == "L2" and result.confidence >= 0.7:
            categorized["knowledge"].append(result)
        elif result.layer == "L3" and result.confidence >= 0.6:
            categorized["workflows"].append(result)
        elif result.layer == "L4" and result.confidence >= 0.5:
            categorized["strategies"].append(result)
        elif result.layer == "L0":
            categorized["evidence"].append(result)
        else:
            categorized["guesses"].append(result)
    
    return categorized
```

#### 2. Flooding Prevention
```python
def _prevent_flooding(self, categorized: dict, query: str) -> dict:
    """Prevent context from overwhelming prompt."""
    total_items = sum(len(items) for items in categorized.values())
    
    # Calculate proportional limits based on query complexity
    query_complexity = len(query.split())
    item_limit = min(
        total_items,
        50 - query_complexity * 2  # More complex = fewer items
    )
    
    # Prioritize by certainty and relevance
    prioritized = {}
    for category, items in categorized.items():
        sorted_items = sorted(items, key=lambda i: i.relevance_score, reverse=True)
        category_limit = {
            "facts": self.fact_limit,
            "knowledge": self.knowledge_limit,
            "workflows": self.knowledge_limit // 2,
            "strategies": self.strategy_limit // 3
        }.get(category, len(sorted_items))
        
        prioritized[category] = sorted_items[:category_limit]
    
    # Ensure minimum items for context
    total_selected = sum(len(items) for items in prioritized.values())
    if total_selected < 5:  # Minimum context items
        # Add more from next certainty level
        self._add_remaining_items(prioritized, total_selected, 5 - total_selected)
    
    return prioritized
```

#### 3. Intelligent Summarization
```python
def _summarize_if_needed(self, results: dict, query: str) -> dict:
    """Summarize large result sets to fit context limits."""
    total_items = sum(len(items) for items in results.values())
    estimated_tokens = self._estimate_tokens(results)
    
    if estimated_tokens <= self.max_context_tokens:
        return {
            "context": results,
            "summarized": False,
            "confidence": self._calculate_group_confidence(results)
        }
    
    # Need summarization
    summary = self._generate_summary(results, query)
    
    return {
        "context": {
            "summary": summary,
            "key_points": self._extract_key_points(results)
        },
        "summarized": True,
        "confidence": summary["confidence"] * 0.9  # Penalty for summarization
    }
```

#### 4. Source Citation
```python
def _add_citations(self, context: dict) -> dict:
    """Add structured source citations to context."""
    cited = {
        "context": [],
        "sources": []
    }
    
    for category, items in context.items():
        for item in items:
            citation = {
                "layer": item.layer,
                "source_id": item.source_id,
                "confidence": item.confidence,
                "accessed_at": item.last_accessed,
                "evidence_chain": self._get_evidence_chain(item.source_id)
            }
            
            cited["context"].append({
                "content": item.content,
                "citation": f"[{item.layer}:{item.source_id}]"
            })
            cited["sources"].append(citation)
    
    return cited
```

#### 5. Fact-Interpretation Separation
```python
def _separate_facts_from_guesses(self, context: dict) -> dict:
    """Separate verified facts from AI interpretations."""
    separated = {
        "facts": [],           # From L1, high confidence
        "interpretations": [],  # AI analysis, lower layers
        "evidence": []         # Supporting raw data
    }
    
    for category, items in context.items():
        if category == "facts":
            separated["facts"].extend(items)
            # Add supporting evidence
            for item in items:
                evidence_chain = self._get_evidence_chain(item.source_id)
                separated["evidence"].extend(evidence_chain)
        elif category in ["knowledge", "workflows", "strategies"]:
            # These are interpretations unless they cite L1 facts
            if not self._cites_l1_facts(items):
                separated["interpretations"].extend(items)
            else:
                separated["facts"].extend(items)
                separated["evidence"].extend(self._get_all_evidence_chains(items))
    
    return separated
```

## 3. LEARNING RULES

### Automatic Learning Engine

**File**: `assistant/learning/learning_engine.py`

```python
class LearningEngine:
    """Automatic pattern detection and memory promotion."""
    
    def __init__(self):
        self.min_occurrence_threshold = 3  # Minimum occurrences to learn
        self.success_rate_threshold = 0.7  # 70% success for promotion
        self.failure_analysis_window = 10  # Analyze last 10 failures
        self.temporal_window_hours = 168  # 7 days for pattern detection
    
    def process_command_output(self, command: str, output: str, success: bool) -> LearningAction:
        """Learn from command execution results."""
        action = None
        
        if success:
            action = self._learn_from_success(command, output)
        else:
            action = self._learn_from_failure(command, output)
        
        return action
    
    def _learn_from_success(self, command: str, output: str) -> LearningAction:
        """Extract learning from successful command."""
        actions = []
        
        # 1. Extract facts from output
        facts = self.fact_extractor.extract_from_evidence(output)
        for fact in facts:
            actions.append(LearningAction(
                type="extract_fact",
                target_layer="L1",
                data=fact.to_dict()
            ))
        
        # 2. Check for repeat patterns
        repeat_count = self._count_recent_repeats(command, output)
        if repeat_count >= self.min_occurrence_threshold:
            # Promote to workflow memory
            workflow = self._build_workflow_from_repeat(command, output, repeat_count)
            actions.append(LearningAction(
                type="promote_workflow",
                target_layer="L3",
                data=workflow.to_dict(),
                confidence=self.success_rate_threshold * (repeat_count / self.min_occurrence_threshold)
            ))
        
        # 3. Extract fix patterns
        fixes = self._extract_fix_patterns(command, output)
        for fix in fixes:
            actions.append(LearningAction(
                type="learn_fix_pattern",
                target_layer="L2",
                data=fix.to_dict(),
                confidence=0.8
            ))
        
        return actions
    
    def _learn_from_failure(self, command: str, output: str) -> LearningAction:
        """Extract learning from failed command."""
        actions = []
        
        # 1. Analyze error patterns
        error_patterns = self._analyze_error_patterns(command, output)
        for pattern in error_patterns:
            actions.append(LearningAction(
                type="learn_failure_pattern",
                target_layer="L1",
                data=pattern.to_dict(),
                confidence=0.6
            ))
        
        # 2. Check for alternative approaches
        alternatives = self._find_alternatives(command, output)
        for alt in alternatives:
            actions.append(LearningAction(
                type="learn_alternative",
                target_layer="L4",
                data=alt.to_dict(),
                confidence=0.7
            ))
        
        return actions
```

### Promotion Rules Engine

**File**: `assistant/learning/promotion_engine.py`

```python
class PromotionEngine:
    """Promote memory items between layers based on validation."""
    
    def __init__(self):
        self.promotion_confidence = {
            "L0→L1": 0.95,  # Raw evidence to facts
            "L1→L2": 0.85,   # Facts to knowledge
            "L2→L3": 0.75,   # Knowledge to workflows
            "L3→L4": 0.65    # Workflows to strategies
        }
        self.user_confirmation_boost = 0.1  # +10% if user confirms
    
    def promote(self, item: MemoryItem, user_confirmation: bool = False) -> PromotionResult:
        """Promote memory item to higher layer."""
        current_layer = self._get_current_layer(item)
        target_layer = self._get_target_layer(current_layer)
        
        if not target_layer:
            return PromotionResult(success=False, reason="Already at highest layer")
        
        # Check promotion criteria
        confidence = item.confidence
        if user_confirmation:
            confidence += self.user_confirmation_boost
        
        if confidence < self.promotion_confidence[f"{current_layer}→{target_layer}"]:
            return PromotionResult(success=False, reason=f"Confidence {confidence} below threshold")
        
        # Check validation status
        if item.validation_status != "validated":
            return PromotionResult(success=False, reason=f"Item not yet validated")
        
        # Promote the item
        promoted_item = self._create_promoted_item(item, target_layer)
        self._store_promoted_item(promoted_item)
        
        # Record promotion for learning
        self._record_promotion(item, promoted_item)
        
        return PromotionResult(
            success=True,
            old_layer=current_layer,
            new_layer=target_layer,
            promoted_id=promoted_item.id,
            confidence=confidence
        )
```

## 4. VERIFICATION ENGINE

### Quality Control System

**File**: `assistant/verification/quality_control.py`

```python
class QualityControl:
    """Multi-dimensional verification of memory quality."""
    
    def __init__(self):
        self.quality_thresholds = {
            "min_confidence": 0.5,      # Minimum acceptable confidence
            "max_stale_days": 90,         # Days before considered stale
            "contradiction_penalty": 0.3,   # Penalty for contradictions
            "hallucination_penalty": 0.5,    # Penalty for hallucinations
            "unsafe_penalty": 0.7              # Penalty for unsafe content
        }
    
    def verify_item(self, item: MemoryItem) -> VerificationResult:
        """Comprehensive verification of a memory item."""
        scores = {}
        
        # 1. Confidence scoring
        scores["confidence"] = self._score_confidence(item)
        
        # 2. Source traceability
        scores["traceability"] = self._score_traceability(item)
        
        # 3. Freshness check
        scores["freshness"] = self._score_freshness(item)
        
        # 4. Contradiction detection
        scores["consistency"] = self._check_consistency(item)
        
        # 5. Safety validation
        scores["safety"] = self._validate_safety(item)
        
        # 6. Hallucination detection
        scores["hallucination_risk"] = self._detect_hallucination(item)
        
        # Calculate overall quality score
        overall_score = self._calculate_overall_score(scores)
        
        # Apply penalties
        if scores["consistency"]["has_contradiction"]:
            overall_score -= self.quality_thresholds["contradiction_penalty"]
        if scores["hallucination_risk"]["is_hallucination"]:
            overall_score -= self.quality_thresholds["hallucination_penalty"]
        if scores["safety"]["is_unsafe"]:
            overall_score -= self.quality_thresholds["unsafe_penalty"]
        
        return VerificationResult(
            item_id=item.id,
            layer=item.layer,
            overall_score=overall_score,
            scores=scores,
            quality_level=self._determine_quality_level(overall_score),
            actions=self._generate_verification_actions(scores)
        )
```

### Verification Components

#### 1. Confidence Scoring
```python
def _score_confidence(self, item: MemoryItem) -> float:
    """Calculate confidence based on source and validation."""
    base_confidence = item.confidence
    
    # Source layer weighting
    layer_weights = {
        "L0": 0.6,  # Raw evidence - lower base
        "L1": 0.8,  # Parsed facts - higher
        "L2": 0.9,  # Knowledge - highest
        "L3": 0.85, # Workflows - high
        "L4": 0.95   # Strategies - highest
    }
    
    weighted_confidence = base_confidence * layer_weights[item.layer]
    
    # Validation history adjustment
    validation_history = self._get_validation_history(item.id)
    if validation_history:
        recent_validations = [v for v in validation_history if v.days_ago < 30]
        if recent_validations:
            avg_validation = sum(v.valid for v in recent_validations) / len(recent_validations)
            weighted_confidence = (weighted_confidence + avg_validation) / 2
    
    return min(weighted_confidence, 1.0)
```

#### 2. Contradiction Detection
```python
def _check_consistency(self, item: MemoryItem) -> dict:
    """Check for contradictions with existing memory."""
    contradictions = []
    
    # Get related items from same layer
    related = self.memory.get_related_items(item.id)
    
    for related_item in related:
        # Direct factual contradictions
        if self._are_contradictory(item, related_item):
            contradictions.append({
                "type": "direct_contradiction",
                "related_id": related_item.id,
                "description": self._describe_contradiction(item, related_item)
            })
        
        # Temporal inconsistencies
        if self._has_temporal_inconsistency(item, related):
            contradictions.append({
                "type": "temporal_inconsistency",
                "related_id": related_item.id,
                "description": "Fact changed since last recorded"
            })
    
    has_contradiction = len(contradictions) > 0
    
    return {
        "has_contradiction": has_contradiction,
        "contradictions": contradictions,
        "consistency_score": 1.0 - (0.2 * len(contradictions))
    }
```

#### 3. Hallucination Prevention
```python
def _detect_hallucination(self, item: MemoryItem) -> dict:
    """Detect potential hallucinations in memory."""
    risk_indicators = []
    
    # 1. Check against evidence sources
    evidence_chain = self.memory.get_evidence_chain(item.id)
    if not evidence_chain:
        risk_indicators.append({
            "type": "no_evidence_source",
            "description": "Item not backed by raw evidence"
        })
    
    # 2. Check for semantic drift
    if item.layer in ["L2", "L3", "L4"]:
        original_sources = self._get_original_sources(item.id)
        if not original_sources:
            risk_indicators.append({
                "type": "semantic_drift",
                "description": "Semantic meaning changed from sources"
            })
    
    # 3. Check for circular reasoning
    if self._has_circular_dependency(item.id):
        risk_indicators.append({
            "type": "circular_reasoning",
            "description": "Item depends on itself or creates circular reference"
        })
    
    # 4. Check for implausible combinations
    if self._has_implausible_content(item):
        risk_indicators.append({
            "type": "implausible_content",
            "description": "Content violates logical constraints"
        })
    
    is_hallucination = len(risk_indicators) > 0
    
    return {
        "is_hallucination": is_hallucination,
        "risk_indicators": risk_indicators,
        "hallucination_score": 0.3 * len(risk_indicators)
    }
```

#### 4. Unsafe Memory Rejection
```python
def _validate_safety(self, item: MemoryItem) -> dict:
    """Validate safety of memory content."""
    violations = []
    
    # 1. Check for dangerous commands
    if self._contains_dangerous_commands(item.content):
        violations.append({
            "type": "dangerous_command",
            "description": "Contains potentially harmful commands"
        })
    
    # 2. Check for credential exposure
    if self._exposes_credentials(item.content):
        violations.append({
            "type": "credential_exposure",
            "description": "May expose sensitive credentials"
        })
    
    # 3. Check for network attacks
    if self._contains_attack_patterns(item.content):
        violations.append({
            "type": "attack_pattern",
            "description": "Contains network attack patterns"
        })
    
    # 4. Check for privilege escalation
    if self._attempts_privilege_escalation(item.content):
        violations.append({
            "type": "privilege_escalation",
            "description": "Attempts to elevate system privileges"
        })
    
    is_unsafe = len(violations) > 0
    
    return {
        "is_unsafe": is_unsafe,
        "violations": violations,
        "safety_score": 1.0 - (0.2 * len(violations))
    }
```

## 5. USAGE INTEGRATION

### Memory Usage by Components

**File**: `assistant/usage/memory_usage.py`

```python
class MemoryUsageTracker:
    """Track how different system components use memory."""
    
    def __init__(self):
        self.usage_log = {
            "planner": [],
            "executor": [],
            "reporter": [],
            "pentest_workflow": [],
            "debugger": []
        }
    
    def track_planner_usage(self, context: PromptContext) -> dict:
        """Track how planner uses memory."""
        usage = {
            "component": "planner",
            "action": "build_plan",
            "memory_layers_used": list(context["sources"]),
            "items_accessed": context["filtered_items"],
            "evidence_cited": len(context.get("sources", [])),
            "confidence_threshold": context["confidence"],
            "timestamp": datetime.now().isoformat()
        }
        self.usage_log["planner"].append(usage)
        return usage
    
    def track_executor_usage(self, plan: ExecutionPlan) -> dict:
        """Track how executor uses memory."""
        usage = {
            "component": "executor",
            "action": "execute_step",
            "memory_accessed": [],
            "steps_executed": 0,
            "workflows_used": [],
            "strategies_applied": [],
            "timestamp": datetime.now().isoformat()
        }
        
        for step in plan.steps:
            memory_used = self._track_step_memory(step)
            usage["memory_accessed"].extend(memory_used)
            usage["steps_executed"] += 1
            
            if step.type == "workflow":
                usage["workflows_used"].append(step.workflow_id)
            elif step.type == "strategy":
                usage["strategies_applied"].append(step.strategy_id)
        
        self.usage_log["executor"].append(usage)
        return usage
```

### Usage Patterns Analysis

```python
class UsageAnalyzer:
    """Analyze memory usage patterns for optimization."""
    
    def analyze_layer_usage(self, usage_log: dict) -> dict:
        """Analyze which memory layers are used most."""
        layer_counts = defaultdict(int)
        
        for usage in usage_log["all_components"]:
            for layer in usage["memory_layers_used"]:
                layer_counts[layer] += 1
        
        total_usage = sum(layer_counts.values())
        
        return {
            "layer_distribution": dict(layer_counts),
            "most_used_layer": max(layer_counts, key=layer_counts.get),
            "usage_diversity": len(set(usage["memory_layers_used"])) / total_usage,
            "underutilized_layers": [
                layer for layer, count in layer_counts.items()
                if count < total_usage * 0.1  # Less than 10% usage
            ]
        }
    
    def analyze_success_patterns(self, learning_actions: list) -> dict:
        """Analyze which learning patterns are most successful."""
        pattern_success = defaultdict(list)
        pattern_count = defaultdict(int)
        
        for action in learning_actions:
            if action.type in ["promote_workflow", "promote_knowledge", "promote_strategy"]:
                success = 1 if action.success else 0
                pattern_success[action.type].append(success)
                pattern_count[action.type] += 1
        
        # Calculate success rates
        pattern_performance = {}
        for pattern_type, successes in pattern_success.items():
            count = pattern_count[pattern_type]
            success_rate = sum(successes) / count if count > 0 else 0
            pattern_performance[pattern_type] = {
                "success_rate": success_rate,
                "total_attempts": count,
                "reliability": success_rate > 0.7
            }
        
        return {
            "pattern_performance": pattern_performance,
            "most_reliable": max(
                (p_type, p_data) for p_type, p_data in pattern_performance.items()
            ),
            "patterns_needing_review": [
                p_type for p_type, p_data in pattern_performance.items()
                if p_data["success_rate"] < 0.5  # Below 50% success
            ]
        }
```

## FAILURE CASES & SAFETY CONTROLS

### Critical Failure Scenarios

```python
FAILURE_CASES = {
    "hallucination": {
        "detection": "Semantic mismatch with evidence",
        "mitigation": "Lower confidence, flag for review",
        "safety": "Block from context builder"
    },
    "memory_contamination": {
        "detection": "Cross-workspace memory in current context",
        "mitigation": "Strict workspace isolation enforcement",
        "safety": "Reject contaminated memory items"
    },
    "stale_information": {
        "detection": "Memory not accessed in >90 days",
        "mitigation": "Automatic expiration + user notification",
        "safety": "Exclude from high-confidence retrieval"
    },
    "overgeneralization": {
        "detection": "Knowledge applied outside original scope",
        "mitigation": "Add scope metadata to knowledge units",
        "safety": "Require explicit scope confirmation"
    },
    "credential_leakage": {
        "detection": "Sensitive credentials in higher layers",
        "mitigation": "Secret redaction at all layer boundaries",
        "safety": "Block credential-containing memory from context"
    },
    "unsafe_workflow": {
        "detection": "Workflow contains dangerous commands",
        "mitigation": "Safety gate validation before promotion",
        "safety": "Block unsafe workflows from execution"
    }
}
```

### Safety Control Implementation

```python
class SafetyControl:
    """Multi-layer safety enforcement."""
    
    def __init__(self):
        this.safety_policies = {
            "max_evidence_items": 10,
            "max_fact_items": 20,
            "min_confidence_for_action": 0.7,
            "require_user_approval": {
                "L3_workflow_execution": True,
                "L4_strategy_application": True,
                "credential_containing": True
            }
        }
    
    def validate_retrieval(self, context: PromptContext) -> SafetyValidation:
        """Validate retrieved context before AI use."""
        violations = []
        
        # Check evidence count
        evidence_count = len([c for c in context["evidence"] if c.startswith("[L0:")])
        if evidence_count > self.safety_policies["max_evidence_items"]:
            violations.append({
                "type": "evidence_overload",
                "message": f"Too much raw evidence ({evidence_count} items)"
            })
        
        # Check confidence levels
        low_confidence_items = [c for c in context["facts"] if c.confidence < 0.5]
        if low_confidence_items:
            violations.append({
                "type": "low_confidence_facts",
                "message": f"{len(low_confidence_items)} low-confidence facts included"
            })
        
        # Check for hallucinations
        hallucinations = self._detect_potential_hallucinations(context)
        if hallucinations:
            violations.append({
                "type": "potential_hallucination",
                "message": f"{len(hallucinations)} potential hallucinations detected"
            })
        
        is_safe = len(violations) == 0
        
        return SafetyValidation(
            is_safe=is_safe,
            violations=violations,
            confidence_penalty=0.2 * len(violations) if not is_safe else 0
        )
```

## RANKING FORMULA

### Multi-Factor Relevance Scoring

```
RELEVANCE_SCORE = (
    TEXT_SIMILARITY * 0.35) +
    (SEMANTIC_MATCH * 0.25 if semantic_match else 0) +
    (GRAPH_PROXIMITY * 0.15 if graph_match else 0) +
    (CONFIDENCE * 0.15) +
    (RECENCY_BONUS * 0.10)
)

Where:
- TEXT_SIMILARITY: Cosine similarity between query and result text
- SEMANTIC_MATCH: Vector similarity score (0-1)
- GRAPH_PROXIMITY: 1 / (graph_distance + 1)
- CONFIDENCE: Normalized confidence score (0-1)
- RECENCY_BONUS: max(0, (90 - days_old) / 90)
```

### Context Assembly Algorithm

```
CONTEXT_ASSEMBLY:
1. Retrieve: Multi-modal search (keyword + semantic + graph + structured)
2. Filter: Apply workspace, target, sensitivity, recency filters
3. Rank: Multi-factor relevance scoring
4. Categorize: Separate into facts, knowledge, workflows, strategies, evidence, guesses
5. Flood Control: Enforce proportional limits by certainty level
6. Summarize: If token limit exceeded, generate concise summary
7. Citate: Add layer:source_id references to all items
8. Structure: Separate facts from interpretations with evidence chains
9. Output: Return structured context with metadata for AI consumption
```

## EXAMPLE FLOW

### Complete Learning Pipeline

```
USER COMMAND: "nmap -sV -p-80,443,8080 example.com"

1. EXECUTE: Tool runner executes nmap
   OUTPUT: Raw scan results

2. EVIDENCE LAYER: Store raw output
   evidence_id = "ev_12345"
   content = "nmap scan results..."
   sensitivity = "internal"
   workspace = "current_project"

3. FACT EXTRACTION: Parse IPs, ports, services
   fact_1 = {"type": "ip", "value": "192.168.1.1", "source": "ev_12345"}
   fact_2 = {"type": "port", "value": "80,443,8080", "source": "ev_12345"}
   fact_3 = {"type": "service", "value": "Apache 2.4.49", "source": "ev_12345"}
   fact_4 = {"type": "domain", "value": "example.com", "source": "ev_12345"}

4. KNOWLEDGE GENERATION: Create reusable findings
   knowledge = {"content": "Port 80: HTTP, Ports 443,8080: HTTPS", 
               "confidence": 0.9, "source_facts": [fact_1, fact_2, fact_3, fact_4]}

5. WORKFLOW DETECTION: Recognize pattern as successful reconnaissance
   pattern = {"commands": ["nmap -sV"], "expected": "open_ports", 
               "success_rate": 0.95, "occurrences": 15}

6. PROMOTION: Promote pattern to workflow
   workflow = {"title": "Web Port Discovery", "steps": [pattern], 
               "confidence": 0.85, "layer": "L3"}

7. VERIFICATION: Validate workflow quality
   score = {"confidence": 0.85, "consistency": 0.9, "safety": 1.0}
   quality_level = "high"

8. FUTURE RECALL: Similar query finds stored workflow
   USER: "Check web ports on target.com"
   RETRIEVAL: Returns workflow from L3 layer
   CONTEXT: "[L3:wf_67890]: Web Port Discovery (confidence: 0.85)"
```

## IMPLEMENTATION PLAN

### Phase 1: Core Retrieval (Weeks 1-2)
**Files**: `assistant/retrieval/*.py`
**Deliverables**:
- Multi-modal retrieval engine
- Context builder with flooding prevention
- Source citation system
- Fact-interpretation separation

### Phase 2: Learning System (Weeks 3-4)
**Files**: `assistant/learning/*.py`
**Deliverables**:
- Pattern detection from command outputs
- Promotion engine between layers
- Automatic workflow synthesis
- Usage tracking for all components

### Phase 3: Verification System (Weeks 5-6)
**Files**: `assistant/verification/*.py`
**Deliverables**:
- Multi-dimensional quality scoring
- Contradiction detection
- Hallucination prevention
- Safety control enforcement
- Unsafe memory rejection

### Phase 4: Integration (Weeks 7-8)
**Files**: Integration and testing
**Deliverables**:
- End-to-end pipeline testing
- Performance benchmarking
- Safety validation
- Documentation completion

## SUCCESS CRITERIA

### Functional Requirements
- [ ] All retrieval modalities operational (keyword, semantic, graph, structured)
- [ ] Context builder prevents flooding with proportional limits
- [ ] Source citations accurate and traceable
- [ ] Learning patterns detected from command outputs
- [ ] Promotion rules enforce confidence thresholds
- [ ] Verification system catches contradictions and hallucinations
- [ ] Safety controls prevent unsafe memory usage

### Quality Requirements
- [ ] Retrieval relevance scoring >0.8 correlation with user judgment
- [ ] Context assembly accuracy >90% on test cases
- [ ] Learning pattern success rate >70%
- [ ] Verification false positive rate <5%
- [ ] Safety validation <1% false positives

### Performance Requirements
- [ ] Multi-modal retrieval <500ms for typical queries
- [ ] Context building <200ms
- [ ] Learning processing <100ms per command
- [ ] Verification scoring <50ms per item

## RISKS & MITIGATION

### Architecture Risks
- **Complexity**: Multi-layer retrieval increases system complexity
- **Performance**: Real-time verification may slow context building
- **False Positives**: Over-aggressive safety controls may block useful memory
- **Learning Drift**: Pattern detection may miss novel approaches
- **Context Loss**: Summarization may lose critical details

### Mitigation Strategies
- **Modular Design**: Each component independently testable
- **Configuration**: Tunable thresholds for different environments
- **Fallback**: Progressive degradation if components fail
- **Monitoring**: Track false positive rates and adjust thresholds
- **User Control**: Allow override of safety controls in trusted environments

## CONCLUSION

Retrieval, learning, and verification system provides complete intelligence layer for AI assistant. Enables high-quality context building, automatic learning from experience, and robust quality control.

**Key Innovation**: Multi-modal retrieval with intelligent ranking + automatic learning from system usage + comprehensive verification across all memory layers.

**Next Steps**: Begin Phase 1 with focus on retrieval engine and context builder infrastructure.