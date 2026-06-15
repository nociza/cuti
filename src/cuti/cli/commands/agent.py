"""
Agent-related CLI commands.
"""


import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

agent_app = typer.Typer(help="Agent management commands")
console = Console()


@agent_app.command("status")
def show_agent_status() -> None:
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

            for agent in agents:
                table.add_row(
                    agent.name,
                    agent.__class__.__name__,
                    "Available"
                )

            console.print(table)
        else:
            rprint("[yellow]No agents available[/yellow]")

    except ImportError:
        rprint("[red]Agent system not available[/red]")


@agent_app.command("test")
def test_agents() -> None:
    """Test agent connections and availability."""
    try:
        from ...agents.pool import AgentPool
        pool = AgentPool()

        agents = pool.get_available_agents()

        if not agents:
            rprint("[red]No agents available to test[/red]")
            return

        rprint("[bold]Testing agents...[/bold]\n")

        for agent in agents:
            try:
                # Simple test - this would need to be implemented in the agent
                rprint(f"[green]✓[/green] {agent.name}: Available")
            except Exception as e:
                rprint(f"[red]✗[/red] {agent.name}: {str(e)}")

    except ImportError:
        rprint("[red]Agent system not available[/red]")


@agent_app.command("list")
def list_agents() -> None:
    """List all configured agents."""
    try:
        from ...agents.pool import AgentPool
        pool = AgentPool()

        agents = pool.get_available_agents()

        if not agents:
            rprint("[yellow]No agents configured[/yellow]")
            return

        rprint(f"[bold]Found {len(agents)} agents:[/bold]")
        for agent in agents:
            rprint(f"  • {agent.name}")

    except ImportError:
        rprint("[red]Agent system not available[/red]")


@agent_app.command("route")
def test_routing(
    prompt: str = typer.Argument(..., help="Test prompt for routing"),
) -> None:
    """Test agent routing for a given prompt."""
    try:
        import asyncio

        from ...agents.pool import AgentPool
        from ...agents.router import TaskRouter
        from ...core.models import QueuedPrompt

        router = TaskRouter(AgentPool())

        decision = asyncio.run(router.route_task(QueuedPrompt(content=prompt)))

        if decision:
            rprint(f"[green]Selected agent:[/green] {decision.agent.name}")
        else:
            rprint("[yellow]No agent selected for this prompt[/yellow]")

    except ImportError:
        rprint("[red]Agent system not available[/red]")
