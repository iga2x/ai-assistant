import os
from pathlib import Path
from typing import List, Dict, Any
from assistant.utils.paths import KNOWLEDGE_DIR
from assistant.memory.secure_knowledge import secure_knowledge_manager

# DEPRECATED: Use secure_knowledge_manager instead
class KnowledgeManager:
    """Deprecated: Use assistant.memory.secure_knowledge.SecureKnowledgeManager instead."""

    def __init__(self):
        self.knowledge_root = KNOWLEDGE_DIR
        import warnings
        warnings.warn(
            "KnowledgeManager is deprecated. Use secure_knowledge_manager from assistant.memory.secure_knowledge instead.",
            DeprecationWarning,
            stacklevel=2
        )

    def add_document(self, filename: str, content: str):
        doc_path = self.knowledge_root / filename
        with open(doc_path, "w") as f:
            f.write(content)

    def search(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """Search for relevant snippets in the knowledge base."""
        results = []
        if not self.knowledge_root.exists():
            return results

        query_words = set(query.lower().split())
        
        for doc_path in self.knowledge_root.glob("*.txt"):
            with open(doc_path, "r") as f:
                content = f.read()
                score = 0
                for word in query_words:
                    if word in content.lower():
                        score += 1
                
                if score > 0:
                    results.append({
                        "filename": doc_path.name,
                        "content": content[:500] + "...", # Snippet
                        "score": score
                    })
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def list_documents(self):
        return [d.name for d in self.knowledge_root.glob("*.txt")]
