from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.console import Console, Group
from datetime import datetime

class TUIDashboard:
    def __init__(self, sys_info):
        self.sys_info = sys_info
        self.layout = Layout()
        self._setup_layout()

    def _setup_layout(self):
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="side", ratio=1),
            Layout(name="body", ratio=3)
        )
        self.layout["side"].split(
            Layout(name="system"),
            Layout(name="tools")
        )

    def update_header(self):
        self.layout["header"].update(
            Panel(
                Text(f"AI Assistant v0.1.0 | {datetime.now().strftime('%H:%M:%S')}", justify="center"),
                style="bold white on blue"
            )
        )

    def update_system_panel(self):
        table = Table.grid(padding=1)
        table.add_column(style="cyan", justify="right")
        table.add_column(style="white")
        
        table.add_row("OS:", self.sys_info.os_name)
        table.add_row("User:", self.sys_info.username)
        table.add_row("IP:", self.sys_info.local_ip)
        table.add_row("Shell:", self.sys_info.shell)
        
        self.layout["system"].update(Panel(table, title="[bold]System Status[/bold]", border_style="cyan"))

    def update_tools_panel(self, tools_list):
        text = Text()
        for tool in tools_list[:10]:
            text.append(f"• {tool}\n", style="green")
        if len(tools_list) > 10:
            text.append("...", style="dim")
            
        self.layout["tools"].update(Panel(text, title="[bold]Available Tools[/bold]", border_style="green"))

    def update_chat(self, chat_renderable):
        self.layout["body"].update(Panel(chat_renderable, title="[bold]Conversation[/bold]", border_style="blue"))

    def update_footer(self, message="Type your command below..."):
        self.layout["footer"].update(Panel(Text(message, justify="center"), border_style="dim"))

    def get_layout(self):
        return self.layout
