import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from assistant.db.database import DatabaseManager
from assistant.db.models import ScanSnapshot, Message, Service
from rich.table import Table
from rich import box

class ReportBuilder:
    def __init__(self, db: DatabaseManager = None):
        self.db = db

    def build_diff_table(self, diff: Dict[str, Any]) -> Table:
        """Create a rich Table for displaying differences."""
        table = Table(title="Scan Comparison (Current vs Previous)", box=box.ROUNDED)
        table.add_column("Port", style="cyan")
        table.add_column("Service", style="magenta")
        table.add_column("Change", style="bold")
        
        for s in diff["added"]:
            table.add_row(f"{s.port}/{s.protocol}", s.service_name, "[bold green]NEW[/bold green]")
            
        for s in diff["removed"]:
            table.add_row(f"{s.port}/{s.protocol}", s.service_name, "[bold red]REMOVED[/bold red]")
            
        for c in diff["changed"]:
            old, new = c["old"], c["new"]
            table.add_row(
                f"{new.port}/{new.protocol}", 
                new.service_name, 
                f"[bold yellow]CHANGED[/bold yellow] ({old.state} -> {new.state})"
            )
            
        if not diff["added"] and not diff["removed"] and not diff["changed"]:
            table.add_row("-", "-", "No changes detected")
            
        return table


    def generate_markdown_report(self, conversation_id: int) -> str:
        """Generate a complete Markdown report for a conversation."""
        from assistant.db.models import AuditLog
        
        # Get Conversation & Messages
        messages = self.db.session.query(Message).filter_by(conversation_id=conversation_id).all()
        
        # Get Audit Logs for the session
        audit_logs = self.db.session.query(AuditLog).all()
        
        # Get Targets
        targets = set()
        for m in messages:
            if "target" in m.content.lower():
                for word in m.content.split():
                    if "." in word or "localhost" in word:
                        targets.add(word.strip(".,?!"))
        
        report = f"# AI Assistant - Session Report\n"
        report += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**Conversation ID:** {conversation_id}\n\n"
        
        report += "## 🛡 Security Audit Summary\n"
        total = len(audit_logs)
        success = len([l for l in audit_logs if l.status == "success"])
        blocked = len([l for l in audit_logs if l.status == "blocked"])
        failed = len([l for l in audit_logs if l.status == "failed"])
        
        report += f"- **Total Commands Attempted:** {total}\n"
        report += f"- **Successful Executions:** {success}\n"
        report += f"- **Blocked by Safety/Scope:** {blocked}\n"
        report += f"- **Execution Failures:** {failed}\n\n"
        
        report += "## 💬 Conversation History\n"
        for m in messages:
            role = m.role.upper()
            report += f"**{role}**: {m.content}\n\n"
        
        if targets:
            report += "## 🔍 Investigation Results\n"
            for target in targets:
                snapshots = self.db.session.query(ScanSnapshot).filter_by(target=target).all()
                if snapshots:
                    report += f"### Target Analysis: {target}\n"
                    for snap in snapshots:
                        report += f"#### Scan: {snap.tool_name} ({snap.created_at})\n"
                        report += "| Port | Protocol | Service | State |\n"
                        report += "|------|----------|---------|-------|\n"
                        for s in snap.services:
                            report += f"| {s.port} | {s.protocol} | {s.service_name} | {s.state} |\n"
                        report += "\n"

        report += "---\n*End of Report*\n"
        return report

    def export_to_file(self, content: str, filepath: Path):
        with open(filepath, "w") as f:
            f.write(content)
        return filepath
