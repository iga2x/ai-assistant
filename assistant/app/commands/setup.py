import click
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import print as rprint

from assistant.config.manager import ConfigManager
from assistant.ai.detector import detect_providers

console = Console()

def select_from_list(items: list, title: str, allow_manual: bool = False):
    """Helper to show a numbered list with pagination."""
    if not items and not allow_manual:
        return None
        
    page_size = 20
    current_page = 0
    total_pages = (len(items) + page_size - 1) // page_size if items else 1
    
    while True:
        console.clear()
        start = current_page * page_size
        end = min(start + page_size, len(items))
        page_items = items[start:end] if items else []
        
        table = Table(title=f"{title} (Page {current_page + 1}/{total_pages})")
        table.add_column("No.", style="dim")
        table.add_column("Option")
        
        for i, item in enumerate(page_items, start + 1):
            table.add_row(str(i), str(item))
            
        console.print(table)
        
        nav_opts = []
        if current_page < total_pages - 1:
            nav_opts.append("[cyan]n[/cyan]: Next Page")
        if current_page > 0:
            nav_opts.append("[cyan]p[/cyan]: Prev Page")
        nav_opts.append("[red]0[/red]: Cancel")
        
        console.print("\n" + " | ".join(nav_opts))
        
        prompt_text = "\nSelect number"
        if total_pages > 1:
            prompt_text += " (n/p to scroll)"
        if allow_manual:
            prompt_text += " or type ID manually"
            
        m_input = Prompt.ask(prompt_text, default="1")
        
        if m_input == "0":
            return None
        if m_input.lower() == "n" and current_page < total_pages - 1:
            current_page += 1
            continue
        if m_input.lower() == "p" and current_page > 0:
            current_page -= 1
            continue
            
        if m_input.isdigit() and 1 <= int(m_input) <= len(items):
            return items[int(m_input)-1]
        
        if allow_manual and m_input.lower() not in ["n", "p", "0"]:
            return m_input
        
        if not items and allow_manual:
            return m_input
            
    return None

@click.command()
def setup():
    """Interactive setup and configuration wizard."""
    mgr = ConfigManager()
    
    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]AI Assistant Setup Wizard[/bold cyan]\n"
            "Configure your models, providers, and system behavior.",
            border_style="cyan"
        ))
        
        console.print("\n[bold]Main Menu:[/bold]")
        console.print("1. [cyan]AI Providers & Models[/cyan] (Select defaults)")
        console.print("2. [cyan]API Key Configuration[/cyan] (OpenAI, Anthropic, Gemini)")
        console.print("3. [cyan]Behavior Settings[/cyan] (Privacy, Approval, Modes)")
        console.print("4. [cyan]Reset Configuration[/cyan]")
        console.print("0. [red]Exit[/red]")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "0"], default="0")
        
        if choice == "1":
            configure_ai(mgr)
        elif choice == "2":
            configure_keys(mgr)
        elif choice == "3":
            configure_behavior(mgr)
        elif choice == "4":
            if Confirm.ask("[red]Reset all settings to default?[/red]"):
                mgr.reset_config()
                console.print("[green]Configuration reset.[/green]")
                Prompt.ask("Press Enter to continue")
        elif choice == "0":
            break

def configure_ai(mgr):
    while True:
        console.clear()
        providers = detect_providers()
        
        table = Table(title="Available AI Providers")
        table.add_column("ID", style="dim")
        table.add_column("Provider")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Available Models")
        
        for i, p in enumerate(providers, 1):
            status = "[green]✔ Available[/green]" if p.is_available else "[red]✘ Unavailable[/red]"
            models = ", ".join(p.models[:3]) + ("..." if len(p.models) > 3 else "")
            table.add_row(str(i), p.name, p.type, status, models or "None")
        
        console.print(table)
        console.print(f"\n[bold]Current Defaults:[/bold]")
        console.print(f"Local: [cyan]{mgr.config.ai.default_local_provider}[/cyan] -> [yellow]{mgr.config.ai.default_local_model}[/yellow]")
        console.print(f"Cloud: [cyan]{mgr.config.ai.default_cloud_provider}[/cyan] -> [yellow]{mgr.config.ai.default_cloud_model}[/yellow]")
        
        console.print("\n[bold]Options:[/bold]")
        console.print("1. Set Default [green]Local[/green] Provider/Model")
        console.print("2. Set Default [blue]Cloud[/blue] Provider/Model")
        console.print("3. Toggle [magenta]Auto-select Model[/magenta] (" + ("ON" if mgr.config.ai.auto_select_model else "OFF") + ")")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "0"], default="0")
        
        if choice == "1":
            locals = [p for p in providers if p.type == "local" and p.is_available]
            if not locals:
                console.print("[red]No local providers available (is Ollama/LM Studio running?)[/red]")
                Prompt.ask("Press Enter to continue")
                continue
            
            p_names = [p.name for p in locals]
            p_choice = select_from_list(p_names, "Select Local Provider")
            if not p_choice: continue
            
            provider = next(p for p in locals if p.name == p_choice)
            
            if provider.models:
                m_choice = select_from_list(provider.models, f"Select model for {provider.name}")
                if m_choice:
                    mgr.config.ai.default_local_provider = provider.name
                    mgr.config.ai.default_local_model = m_choice
                    mgr.save_config()
                    console.print(f"[green]✔ Local default set to {provider.name}/{m_choice}[/green]")
            else:
                console.print("[yellow]No models found for this provider.[/yellow]")
            Prompt.ask("Press Enter to continue")
            
        elif choice == "2":
            clouds = [p for p in providers if p.type == "cloud"]
            p_names = [p.name for p in clouds]
            p_choice = select_from_list(p_names, "Select Cloud Provider")
            if not p_choice: continue
            
            provider = next(p for p in clouds if p.name == p_choice)
            
            # For models, allow manual entry as backup
            m_choice = select_from_list(provider.models, f"Select model for {provider.name}", allow_manual=True)
            if not m_choice:
                # If no models detected, use presets
                common_models = {
                    "openai": ["gpt-4o", "gpt-4o-mini", "o1-preview"],
                    "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"],
                    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"],
                    "openrouter": ["meta-llama/llama-3.1-405b-instruct", "google/gemini-pro-1.5"],
                    "groq": ["llama-3.1-70b-versatile", "llama3-8b-8192"],
                    "deepseek": ["deepseek-chat", "deepseek-coder"],
                    "mistral": ["mistral-large-latest", "mistral-small-latest"],
                    "zai": ["glm-4", "glm-4v"],
                    "zai_coding": ["codegeex-4"]
                }
                presets = common_models.get(provider.name, ["default"])
                m_choice = select_from_list(presets, f"Select model preset for {provider.name}", allow_manual=True)

            if m_choice:
                mgr.config.ai.default_cloud_provider = provider.name
                mgr.config.ai.default_cloud_model = m_choice
                mgr.save_config()
                console.print(f"[green]✔ Cloud default set to {provider.name}/{m_choice}[/green]")
            Prompt.ask("Press Enter to continue")
            
        elif choice == "3":
            mgr.config.ai.auto_select_model = not mgr.config.ai.auto_select_model
            mgr.save_config()
            
        elif choice == "0":
            break

def configure_keys(mgr):
    from assistant.memory import MemoryManager
    memory = MemoryManager()

    while True:
        console.clear()
        console.print(Panel("[bold]API Key Configuration[/bold]\nKeys can be stored securely in the encrypted database or as environment variables."))
        
        stored_secrets = memory.get_all_facts().get("secrets", {})
        
        keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or stored_secrets.get("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY") or stored_secrets.get("ANTHROPIC_API_KEY"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY") or stored_secrets.get("GOOGLE_API_KEY"),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY") or stored_secrets.get("OPENROUTER_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY") or stored_secrets.get("GROQ_API_KEY"),
            "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY") or stored_secrets.get("DEEPSEEK_API_KEY"),
            "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY") or stored_secrets.get("MISTRAL_API_KEY"),
            "ZAI_API_KEY": os.getenv("ZAI_API_KEY") or stored_secrets.get("ZAI_API_KEY")
        }
        
        table = Table()
        table.add_column("Provider")
        table.add_column("Env Variable")
        table.add_column("Status")
        
        table.add_row("OpenAI", "OPENAI_API_KEY", "[green]SET[/green]" if keys["OPENAI_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("Anthropic", "ANTHROPIC_API_KEY", "[green]SET[/green]" if keys["ANTHROPIC_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("Gemini", "GOOGLE_API_KEY", "[green]SET[/green]" if keys["GOOGLE_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("OpenRouter", "OPENROUTER_API_KEY", "[green]SET[/green]" if keys["OPENROUTER_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("Groq", "GROQ_API_KEY", "[green]SET[/green]" if keys["GROQ_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("DeepSeek", "DEEPSEEK_API_KEY", "[green]SET[/green]" if keys["DEEPSEEK_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("Mistral", "MISTRAL_API_KEY", "[green]SET[/green]" if keys["MISTRAL_API_KEY"] else "[red]MISSING[/red]")
        table.add_row("Z.AI", "ZAI_API_KEY", "[green]SET[/green]" if keys["ZAI_API_KEY"] else "[red]MISSING[/red]")
        
        console.print(table)
        console.print("\n[dim]Note: Secrets are stored encrypted in memory.db. Environment variables take precedence.[/dim]")
        
        console.print("\n[bold]Options:[/bold]")
        console.print("1. Set OpenAI Key")
        console.print("2. Set Anthropic Key")
        console.print("3. Set Gemini Key")
        console.print("4. Set OpenRouter Key")
        console.print("5. Set Groq Key")
        console.print("6. Set DeepSeek Key")
        console.print("7. Set Mistral Key")
        console.print("8. Set Z.AI Key")
        console.print("0. Back")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "0"], default="0")
        
        if choice == "0":
            break
        
        var_map = {
            "1": "OPENAI_API_KEY", 
            "2": "ANTHROPIC_API_KEY", 
            "3": "GOOGLE_API_KEY",
            "4": "OPENROUTER_API_KEY",
            "5": "GROQ_API_KEY",
            "6": "DEEPSEEK_API_KEY",
            "7": "MISTRAL_API_KEY",
            "8": "ZAI_API_KEY"
        }
        var_name = var_map[choice]
        key_val = Prompt.ask(f"Enter value for {var_name}", password=True)
        
        if key_val:
            # Save to Encrypted DB
            memory.set_secret(var_name, key_val)
            console.print(f"[bold green]✔ Secret saved securely to encrypted database.[/bold green]")
            
            if Confirm.ask("Would you also like to save this to a local .env file (UNSAFE, plain text)?"):
                with open(".env", "a") as f:
                    f.write(f"\n{var_name}=\"{key_val}\"")
                console.print("[green]Saved to .env[/green]")
            Prompt.ask("Press Enter to continue")

def configure_behavior(mgr):
    while True:
        console.clear()
        console.print(Panel("[bold]Behavior & Privacy Settings[/bold]"))
        
        options = [
            ("Execution Mode", "execution.mode", ["active", "learning"]),
            ("Ask before Cloud", "ai.ask_before_cloud", [True, False]),
            ("Require Approval for Security Tools", "execution.require_approval_for_security_tools", [True, False]),
            ("Block Unknown Targets", "security.block_unknown_targets", [True, False]),
            ("Show AI Reasoning", "debug.show_ai_reasoning", [True, False])
        ]
        
        table = Table()
        table.add_column("ID", style="dim")
        table.add_column("Setting")
        table.add_column("Current Value", style="bold cyan")
        
        for i, (label, key, _) in enumerate(options, 1):
            parts = key.split(".")
            val = getattr(getattr(mgr.config, parts[0]), parts[1])
            table.add_row(str(i), label, str(val))
            
        console.print(table)
        console.print("\n0. Back")
        
        choice = IntPrompt.ask("\nSelect setting to toggle/change", default=0)
        
        if choice == 0:
            break
        
        if 1 <= choice <= len(options):
            label, key, vals = options[choice-1]
            parts = key.split(".")
            section = getattr(mgr.config, parts[0])
            current = getattr(section, parts[1])
            
            if isinstance(vals, list) and len(vals) == 2 and isinstance(vals[0], bool):
                # Toggle
                setattr(section, parts[1], not current)
            elif isinstance(vals, list):
                # Select from list
                new_val = Prompt.ask(f"Select value for {label}", choices=vals)
                setattr(section, parts[1], new_val)
            
            mgr.save_config()
            console.print(f"[green]✔ {label} updated.[/green]")
            Prompt.ask("Press Enter to continue")
