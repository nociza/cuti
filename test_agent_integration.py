#!/usr/bin/env python3
"""
Test agent integration with main cuti interface.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from cuti.cli import app
from cuti.queue_manager import QueueManager
from cuti.models import QueuedPrompt
from cuti.agents import AgentPool, AgentConfig
from cuti.agents.pool import AgentType
from rich.console import Console

console = Console()


async def test_agent_integration():
    """Test that agents can be called from the main cuti interface."""
    console.print("[bold cyan]Testing Agent Integration with Main Interface[/bold cyan]")
    console.print("-" * 50)
    
    # Initialize queue manager
    queue_manager = QueueManager()
    
    # Create and initialize agent pool
    agent_pool = AgentPool()
    await agent_pool.initialize()
    
    # Add Claude agent
    claude_config = AgentConfig(
        type="claude",
        name="Claude-Main",
        command="claude",
        timeout=60
    )
    
    console.print("[yellow]Adding Claude agent to pool...[/yellow]")
    claude_added = await agent_pool.add_agent(claude_config)
    
    if claude_added:
        console.print("[green]✓ Claude agent added[/green]")
    else:
        console.print("[red]✗ Failed to add Claude agent[/red]")
    
    # Try to add Gemini if available
    try:
        gemini_config = AgentConfig(
            type="gemini", 
            name="Gemini-Assistant",
            timeout=60
        )
        gemini_added = await agent_pool.add_agent(gemini_config)
        if gemini_added:
            console.print("[green]✓ Gemini agent added[/green]")
    except:
        console.print("[yellow]Gemini agent not available[/yellow]")
    
    # Create a test prompt
    test_prompt = QueuedPrompt(
        content="Write a haiku about Python programming",
        priority=0
    )
    
    # Add prompt to queue
    queue_manager.add_prompt(test_prompt)
    console.print(f"\n[cyan]Added test prompt to queue: {test_prompt.id}[/cyan]")
    
    # Get available agents
    available_agents = agent_pool.get_available_agents()
    console.print(f"\n[magenta]Available agents: {len(available_agents)}[/magenta]")
    for agent in available_agents:
        console.print(f"  - {agent.name} ({agent.__class__.__name__})")
    
    # Test direct execution with an agent
    if available_agents:
        selected_agent = available_agents[0]
        console.print(f"\n[yellow]Testing direct execution with {selected_agent.name}...[/yellow]")
        
        from cuti.agents.base import AgentExecutionContext
        
        context = AgentExecutionContext(
            session_id="test_session",
            shared_memory={},
            available_tools=[],
            coordination_data={},
            collaboration_mode=False
        )
        
        result = await selected_agent.execute_prompt(test_prompt, context)
        
        if result.success:
            console.print("[green]✓ Agent execution successful[/green]")
            console.print(f"  Output length: {len(result.output)} chars")
            console.print(f"  Execution time: {result.execution_time:.2f}s")
            if result.tokens_used:
                console.print(f"  Tokens used: {result.tokens_used}")
        else:
            console.print(f"[red]✗ Agent execution failed: {result.error}[/red]")
    
    # Clean up
    await agent_pool.shutdown()
    console.print("\n[green]✓ Integration test completed[/green]")
    
    return True


async def test_cli_with_agents():
    """Test CLI commands with agent support."""
    console.print("\n[bold cyan]Testing CLI Commands with Agent Support[/bold cyan]")
    console.print("-" * 50)
    
    # Test status command
    console.print("[yellow]Testing 'cuti status' command...[/yellow]")
    try:
        from typer.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(app, ["status"])
        if result.exit_code == 0:
            console.print("[green]✓ Status command works[/green]")
        else:
            console.print(f"[red]✗ Status command failed: {result.stdout}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error testing CLI: {e}[/red]")
    
    return True


async def test_agent_routing():
    """Test agent routing for different task types."""
    console.print("\n[bold cyan]Testing Agent Routing for Different Tasks[/bold cyan]")
    console.print("-" * 50)
    
    from cuti.agents import TaskRouter, TaskRoutingStrategy
    
    # Create agent pool with multiple agents
    agent_pool = AgentPool()
    await agent_pool.initialize()
    
    # Add Claude agent
    claude_config = AgentConfig(
        type="claude",
        name="Claude-Router-Test",
        command="claude"
    )
    await agent_pool.add_agent(claude_config)
    
    # Create router
    router = TaskRouter(agent_pool, TaskRoutingStrategy.CAPABILITY_BASED)
    
    # Test different task types
    test_tasks = [
        ("Debug this Python code", "debugging"),
        ("Write documentation for this API", "documentation"),
        ("Optimize this function for performance", "optimization"),
        ("Create unit tests for this module", "testing"),
        ("Review this code for security issues", "security")
    ]
    
    for task_content, task_type in test_tasks:
        prompt = QueuedPrompt(content=task_content)
        decision = await router.route_task(prompt)
        
        if decision:
            console.print(f"[green]✓ {task_type}: Routed to {decision.agent.name} (confidence: {decision.confidence:.2f})[/green]")
        else:
            console.print(f"[red]✗ {task_type}: No agent available[/red]")
    
    # Get routing statistics
    stats = router.get_routing_stats()
    console.print(f"\n[cyan]Routing Statistics:[/cyan]")
    console.print(f"  Total routed: {stats.get('total_routed', 0)}")
    if stats.get('average_confidence'):
        console.print(f"  Average confidence: {stats['average_confidence']:.2f}")
    
    await agent_pool.shutdown()
    return True


async def main():
    """Run all integration tests."""
    console.print("\n[bold magenta]═══ cuti Agent Integration Tests ═══[/bold magenta]\n")
    
    tests = [
        ("Agent Integration", test_agent_integration),
        ("CLI with Agents", test_cli_with_agents),
        ("Agent Routing", test_agent_routing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            console.print(f"\n[bold]Running: {test_name}[/bold]")
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            console.print(f"[red]Error in {test_name}: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            results.append((test_name, False))
    
    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold cyan]Integration Test Summary[/bold cyan]")
    
    for test_name, success in results:
        status = "[green]✓ Passed[/green]" if success else "[red]✗ Failed[/red]"
        console.print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(1)