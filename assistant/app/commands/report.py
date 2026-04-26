import click
from rich.console import Console
from pathlib import Path
from datetime import datetime
from assistant.db.database import DatabaseManager
from assistant.analysis.report_builder import ReportBuilder

console = Console()

@click.group()
def report():
    """Generate and manage reports."""
    pass

@report.command(name="generate")
@click.option("--output", "-o", help="Output file path")
def report_generate(output):
    """Generate a report for the latest conversation."""
    db = DatabaseManager()
    conv = db.session.query(db.Conversation).order_by(db.Conversation.created_at.desc()).first()
    if not conv:
        console.print("[red]No conversations found.[/red]")
        return
    exporter = ReportBuilder(db)
    content = exporter.generate_markdown_report(conv.id)
    if not output:
        output = f"report_{conv.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    exporter.export_to_file(content, Path(output))
    console.print(f"Report generated: {output}")
