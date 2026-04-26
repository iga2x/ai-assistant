import ipaddress
from typing import List, Optional
from assistant.db.database import DatabaseManager
from assistant.db.models import ScopeItem

class ScopeManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def add_scope(self, target: str, target_type: Optional[str] = None):
        """Add a target to the scope."""
        if not target_type:
            target_type = self._detect_type(target)
        
        item = ScopeItem(target=target, target_type=target_type)
        self.db.session.add(item)
        self.db.session.commit()

    def is_in_scope(self, target: str) -> bool:
        """Check if a target is within the allowed scope."""
        scope_items = self.db.session.query(ScopeItem).all()
        
        for item in scope_items:
            if item.target_type == "domain":
                if target == item.target or target.endswith("." + item.target):
                    return True
            elif item.target_type == "ip":
                if target == item.target:
                    return True
            elif item.target_type == "cidr":
                try:
                    if ipaddress.ip_address(target) in ipaddress.ip_network(item.target):
                        return True
                except ValueError:
                    pass
        return False

    def _detect_type(self, target: str) -> str:
        if "/" in target:
            return "cidr"
        try:
            ipaddress.ip_address(target)
            return "ip"
        except ValueError:
            return "domain"

    def get_all(self) -> List[ScopeItem]:
        return self.db.session.query(ScopeItem).all()
