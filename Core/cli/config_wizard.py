"""
Core/cli/config_wizard.py

Story 7.4 — API Key Management UI (Interactive Wizard)
"""
from __future__ import annotations

import os
import re
import asyncio
from typing import Type
import dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from Core.plugins.manager import PluginManager
from Core.plugins.base import IntelligencePlugin

ENV_PATH = os.path.join(os.getcwd(), ".env")

console = Console()

def get_env_key_name(plugin_name: str) -> str:
    """Matches settings.py behavior for extracting key."""
    normalized = re.sub(r'[^A-Za-z0-9]', '_', plugin_name).upper()
    return f"MH_{normalized}_API_KEY"


async def validate_plugin_key(plugin_cls: Type[IntelligencePlugin], api_key: str) -> tuple[bool, str]:
    """
    Test the API key to ensure it is valid with a dummy query.
    """
    # Instantiate plugin directly with the test key
    plugin = plugin_cls(api_key=api_key)
    target = "test@example.com"
    target_type = "EMAIL"
    
    # Specific plugin fallbacks
    if plugin.name == "Shodan":
        target = "8.8.8.8"
        target_type = "IP"
        
    result = await plugin.check(target, target_type)
    
    # Validation logic
    if result.is_success:
        return True, "Key is valid."
    
    if "401" in (result.error_message or ""):
        return False, "401 Unauthorized - Invalid API Key."
        
    if "429" in (result.error_message or ""):
        return True, "429 Key is valid (Rate limit exceeded, but format accepted)."
        
    if "only supports" in (result.error_message or ""):
        return False, f"Validation failure - unsupported target type: {result.error_message}"
        
    # Other network errors — we can't be absolutely sure, but we will let it through
    return True, f"Could not fully validate due to network: {result.error_message}"


def _get_key_status(env_key: str) -> str:
    # Refresh .env variables locally for accuracy
    dotenv.load_dotenv(ENV_PATH, override=True)
    val = os.environ.get(env_key)
    if not val:
        return "[bold red]Missing[/bold red]"
    return "[bold green]Configured[/bold green]"


def display_wizard() -> None:
    """Main interactive loop for API Key UI."""
    console.print("\n[bold blue]Mr.Holmes[/bold blue] — [white]API Key Management Wizard[/white]")
    
    # Ensure .env exists
    if not os.path.exists(ENV_PATH):
        open(ENV_PATH, 'a').close()
        
    manager = PluginManager()
    plugins = {p_cls.name: p_cls for p_cls in manager.plugins if p_cls(api_key="").requires_api_key}
    
    if not plugins:
        console.print("[yellow]No plugins require an API key at this time.[/yellow]")
        return
        
    plugin_list = list(plugins.values())
    
    while True:
        table = Table(title="External Intelligence Plugins", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Plugin Name", min_width=20)
        table.add_column("Environment Key", min_width=30)
        table.add_column("Status")
        
        for idx, p_cls in enumerate(plugin_list, 1):
            env_key = get_env_key_name(p_cls.name)
            status = _get_key_status(env_key)
            table.add_row(str(idx), p_cls.name, env_key, status)
            
        console.print(table)
        
        console.print("\nType [bold cyan]ID[/bold cyan] to configure a plugin, or [bold cyan]0 / q[/bold cyan] to Exit.")
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice in ('0', 'q', 'quit', 'exit'):
            break
            
        if not choice.isdigit():
            console.print("[red]Invalid choice. Please enter a number.[/red]")
            continue
            
        idx = int(choice)
        if idx < 1 or idx > len(plugin_list):
            console.print("[red]ID out of range.[/red]")
            continue
            
        selected_plugin_cls = plugin_list[idx - 1]
        plugin_name = selected_plugin_cls.name
        env_key = get_env_key_name(plugin_name)
        
        console.print(f"\n[bold]Configuring:[/bold] {plugin_name} ([dim]{env_key}[/dim])")
        new_key = Prompt.ask("Enter new API key (Leave empty to remove)", password=True).strip()
        
        if not new_key:
            if Confirm.ask(f"Are you sure you want to remove the key for {plugin_name}?"):
                dotenv.set_key(ENV_PATH, env_key, "")
                os.environ.pop(env_key, None)
                console.print(f"[green]Removed key for {plugin_name}.[/green]\n")
            continue
            
        console.print("[yellow]Validating key with API server...[/yellow]")
        is_valid, msg = asyncio.run(validate_plugin_key(selected_plugin_cls, new_key))
        
        if is_valid:
            dotenv.set_key(ENV_PATH, env_key, new_key)
            os.environ[env_key] = new_key
            console.print(f"[green]Success! Key saved for {plugin_name}.[/green]\n")
        else:
            console.print(f"[bold red]Validation Failed:[/bold red] {msg}")
            if Confirm.ask("Validation failed. Force save key anyway?", default=False):
                dotenv.set_key(ENV_PATH, env_key, new_key)
                os.environ[env_key] = new_key
                console.print(f"[yellow]Forced save for {plugin_name}.[/yellow]\n")
            else:
                console.print("[dim]Operation cancelled.[/dim]\n")


def invoke_api_key_wizard() -> int:
    """Entry point for MrHolmes.py"""
    try:
        display_wizard()
        return 0
    except KeyboardInterrupt:
        console.print("\n[dim]Wizard exited.[/dim]")
        return 0
    except Exception as e:
        console.print(f"\n[bold red]Wizard crashed:[/bold red] {e}")
        return 1
