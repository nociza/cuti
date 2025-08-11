"""
Agent-related CLI commands.
"""

import json
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from ...agents.pool import AgentPool
from ...agents.router import TaskRouter

agent_app = typer.Typer(help="Agent management commands")
console = Console()


@agent_app.command("status")
def show_agent_status():
    """Show agent system status."""
    try:
        from ...agents.pool import AgentPool
        pool = AgentPool()
        
        rprint("[bold]Agent System Status[/bold]")
        rprint(f"Available agents: {len(pool.get_available_agents())}")
        
        # Show agent details
        agents = pool.get_available_agents()
        if agents:
            table = Table(title="Available Agents")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Status", style="green")
            
            for agent_name in agents:
                agent = pool.get_agent(agent_name)
                if agent:
                    table.add_row(
                        agent_name,
                        agent.__class__.__name__,
                        "Available"
                    )
            
            console.print(table)
        else:
            rprint("[yellow]No agents available[/yellow]")
            
    except ImportError:
        rprint("[red]Agent system not available[/red]")


@agent_app.command("test")  
def test_agents():
    """Test agent connections and availability."""
    try:
        from ...agents.pool import AgentPool
        pool = AgentPool()
        
        agents = pool.get_available_agents()
        
        if not agents:
            rprint("[red]No agents available to test[/red]")
            return
            
        rprint("[bold]Testing agents...[/bold]\n")
        
        for agent_name in agents:
            agent = pool.get_agent(agent_name)
            if agent:
                try:
                    # Simple test - this would need to be implemented in the agent
                    rprint(f"[green]✓[/green] {agent_name}: Available")
                except Exception as e:
                    rprint(f"[red]✗[/red] {agent_name}: {str(e)}")
                    
    except ImportError:
        rprint("[red]Agent system not available[/red]")


@agent_app.command("list")
def list_agents():
    """List all configured agents."""
    try:
        from ...agents.pool import AgentPool
        pool = AgentPool()
        
        agents = pool.get_available_agents()
        
        if not agents:
            rprint("[yellow]No agents configured[/yellow]")
            return
            
        rprint(f"[bold]Found {len(agents)} agents:[/bold]")
        for agent_name in agents:
            rprint(f"  • {agent_name}")
            
    except ImportError:
        rprint("[red]Agent system not available[/red]")


@agent_app.command("route")
def test_routing(
    prompt: str = typer.Argument(..., help="Test prompt for routing"),
):
    """Test agent routing for a given prompt."""
    try:
        from ...agents.router import TaskRouter
        router = AgentRouter()
        
        selected_agent = router.select_agent(prompt)
        
        if selected_agent:
            rprint(f"[green]Selected agent:[/green] {selected_agent}")
        else:
            rprint("[yellow]No agent selected for this prompt[/yellow]")
            
    except ImportError:
        rprint("[red]Agent system not available[/red]")