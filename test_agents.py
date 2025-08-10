#!/usr/bin/env python3
"""
Comprehensive test script for agent implementation.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from cuti.agents import (
    AgentPool,
    AgentConfig,
    TaskRouter,
    TaskRoutingStrategy,
    CoordinationEngine,
    AgentCapability
)
from cuti.agents.pool import AgentType, AgentPoolConfig
from cuti.models import QueuedPrompt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()


async def test_gemini_agent():
    """Test Gemini agent creation and basic functionality."""
    console.print("\n[bold cyan]Testing Gemini Agent[/bold cyan]")
    console.print("-" * 50)
    
    # Create agent pool
    pool_config = AgentPoolConfig(
        max_agents=5,
        health_check_interval=30
    )
    pool = AgentPool(pool_config)
    await pool.initialize()
    
    # Create Gemini agent configuration
    gemini_config = AgentConfig(
        type="gemini",
        name="Gemini-1",
        api_key_env="GOOGLE_API_KEY",
        timeout=60,
        working_directory="."
    )
    
    # Add Gemini agent to pool
    console.print("[yellow]Adding Gemini agent to pool...[/yellow]")
    success = await pool.add_agent(gemini_config)
    
    if success:
        console.print("[green]✓ Gemini agent added successfully[/green]")
        
        # Get the agent
        agent = pool.get_agent("Gemini-1")
        if agent:
            # Display agent info
            table = Table(title="Gemini Agent Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="magenta")
            
            table.add_row("Name", agent.name)
            table.add_row("Status", agent.status.value)
            table.add_row("Max Context Tokens", f"{agent.metadata.max_context_tokens:,}")
            table.add_row("Supports Streaming", str(agent.metadata.supports_streaming))
            table.add_row("Supports Multimodal", str(agent.metadata.supports_multimodal))
            table.add_row("Capabilities", str(len(agent.metadata.capabilities)))
            
            console.print(table)
            
            # Test health check
            console.print("\n[yellow]Testing health check...[/yellow]")
            is_healthy = await agent.health_check()
            if is_healthy:
                console.print("[green]✓ Agent is healthy[/green]")
            else:
                console.print("[red]✗ Agent health check failed[/red]")
    else:
        console.print("[red]✗ Failed to add Gemini agent[/red]")
        console.print("[yellow]Make sure GOOGLE_API_KEY is set and gemini CLI is installed[/yellow]")
        console.print("[dim]Install with: pip install gemini-cli[/dim]")
    
    await pool.shutdown()
    return success


async def test_claude_agent():
    """Test Claude agent creation and basic functionality."""
    console.print("\n[bold cyan]Testing Claude Agent[/bold cyan]")
    console.print("-" * 50)
    
    # Create agent pool
    pool = AgentPool()
    await pool.initialize()
    
    # Create Claude agent configuration
    claude_config = AgentConfig(
        type="claude",
        name="Claude-1",
        command="claude",  # or path to claude executable
        timeout=120,
        working_directory="."
    )
    
    # Add Claude agent to pool
    console.print("[yellow]Adding Claude agent to pool...[/yellow]")
    success = await pool.add_agent(claude_config)
    
    if success:
        console.print("[green]✓ Claude agent added successfully[/green]")
        
        # Get the agent
        agent = pool.get_agent("Claude-1")
        if agent:
            # Display agent info
            table = Table(title="Claude Agent Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="magenta")
            
            table.add_row("Name", agent.name)
            table.add_row("Status", agent.status.value)
            table.add_row("Max Context Tokens", f"{agent.metadata.max_context_tokens:,}")
            table.add_row("Supports Streaming", str(agent.metadata.supports_streaming))
            table.add_row("Capabilities", str(len(agent.metadata.capabilities)))
            
            console.print(table)
    else:
        console.print("[red]✗ Failed to add Claude agent[/red]")
        console.print("[yellow]Make sure Claude Desktop is installed and CLI is available[/yellow]")
    
    await pool.shutdown()
    return success


async def test_multi_agent_execution():
    """Test multi-agent task execution."""
    console.print("\n[bold cyan]Testing Multi-Agent Execution[/bold cyan]")
    console.print("-" * 50)
    
    # Create agent pool
    pool = AgentPool()
    await pool.initialize()
    
    # Try to add both agents
    agents_added = []
    
    # Add Claude agent
    claude_config = AgentConfig(
        type="claude",
        name="Claude-Primary",
        command="claude",
        timeout=60
    )
    if await pool.add_agent(claude_config):
        agents_added.append("Claude-Primary")
        console.print("[green]✓ Added Claude agent[/green]")
    
    # Add Gemini agent
    gemini_config = AgentConfig(
        type="gemini",
        name="Gemini-Assistant",
        api_key_env="GOOGLE_API_KEY",
        timeout=60
    )
    if await pool.add_agent(gemini_config):
        agents_added.append("Gemini-Assistant")
        console.print("[green]✓ Added Gemini agent[/green]")
    
    if not agents_added:
        console.print("[red]No agents available for testing[/red]")
        await pool.shutdown()
        return False
    
    # Create a test prompt
    test_prompt = QueuedPrompt(
        content="Write a simple Python function that calculates the factorial of a number",
        priority=0
    )
    
    # Test task routing
    console.print("\n[yellow]Testing task routing...[/yellow]")
    router = TaskRouter(pool, TaskRoutingStrategy.CAPABILITY_BASED)
    decision = await router.route_task(test_prompt)
    
    if decision:
        console.print(f"[green]✓ Task routed to: {decision.agent.name}[/green]")
        console.print(f"  Confidence: {decision.confidence:.2f}")
        if decision.estimated_time:
            console.print(f"  Estimated time: {decision.estimated_time}s")
        if decision.estimated_cost:
            console.print(f"  Estimated cost: ${decision.estimated_cost:.4f}")
    
    # Test coordination engine
    if len(agents_added) > 1:
        console.print("\n[yellow]Testing collaborative execution...[/yellow]")
        coordinator = CoordinationEngine(pool, router)
        
        # Execute with collaboration
        from cuti.agents.base import AgentExecutionContext
        
        result = await coordinator.execute_collaborative_task(
            test_prompt,
            agents=agents_added[:2],
            parallel=True
        )
        
        if result.success:
            console.print("[green]✓ Collaborative execution successful[/green]")
            console.print(f"  Tokens used: {result.tokens_used}")
            console.print(f"  Execution time: {result.execution_time:.2f}s")
        else:
            console.print(f"[red]✗ Execution failed: {result.error}[/red]")
    
    # Display pool statistics
    stats = pool.get_pool_stats()
    
    table = Table(title="Agent Pool Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Agents", str(stats['total_agents']))
    table.add_row("Available", str(stats['available_agents']))
    table.add_row("Busy", str(stats['busy_agents']))
    table.add_row("Error", str(stats['error_agents']))
    table.add_row("Capabilities Covered", str(stats['capabilities_covered']))
    
    console.print(table)
    
    await pool.shutdown()
    return True


async def test_agent_capabilities():
    """Test agent capability detection and routing."""
    console.print("\n[bold cyan]Testing Agent Capabilities[/bold cyan]")
    console.print("-" * 50)
    
    # Create test prompts with different requirements
    test_prompts = [
        ("Debug this Python code and fix any errors", AgentCapability.DEBUGGING),
        ("Generate comprehensive documentation for this API", AgentCapability.DOCUMENTATION),
        ("Optimize this function for better performance", AgentCapability.PERFORMANCE_OPTIMIZATION),
        ("Analyze this dataset and provide insights", AgentCapability.DATA_ANALYSIS),
        ("Review this code for security vulnerabilities", AgentCapability.SECURITY_ANALYSIS),
    ]
    
    pool = AgentPool()
    await pool.initialize()
    
    # Add test agents
    claude_config = AgentConfig(type="claude", name="Claude-Test")
    gemini_config = AgentConfig(type="gemini", name="Gemini-Test")
    
    await pool.add_agent(claude_config)
    await pool.add_agent(gemini_config)
    
    router = TaskRouter(pool, TaskRoutingStrategy.CAPABILITY_BASED)
    
    # Test each prompt
    results_table = Table(title="Capability Routing Results")
    results_table.add_column("Task", style="cyan")
    results_table.add_column("Expected Capability", style="yellow")
    results_table.add_column("Selected Agent", style="magenta")
    results_table.add_column("Confidence", style="green")
    
    for prompt_text, expected_cap in test_prompts:
        prompt = QueuedPrompt(content=prompt_text)
        decision = await router.route_task(prompt)
        
        if decision:
            results_table.add_row(
                prompt_text[:40] + "...",
                expected_cap.value,
                decision.agent.name,
                f"{decision.confidence:.2f}"
            )
    
    console.print(results_table)
    
    await pool.shutdown()
    return True


async def test_installation_check():
    """Check if required tools are installed."""
    console.print("\n[bold cyan]Checking Tool Installation[/bold cyan]")
    console.print("-" * 50)
    
    checks = []
    
    # Check Claude
    try:
        import subprocess
        result = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=5)
        claude_installed = result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        claude_installed = False
    
    checks.append(("Claude CLI", claude_installed))
    
    # Check Gemini
    try:
        result = subprocess.run(['gemini', '--version'], capture_output=True, text=True, timeout=5)
        gemini_installed = result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        gemini_installed = False
    
    checks.append(("Gemini CLI", gemini_installed))
    
    # Check API keys
    google_api_key = bool(os.environ.get('GOOGLE_API_KEY'))
    checks.append(("GOOGLE_API_KEY", google_api_key))
    
    # Display results
    table = Table(title="Installation Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    
    for component, installed in checks:
        status = "[green]✓ Installed[/green]" if installed else "[red]✗ Not Found[/red]"
        table.add_row(component, status)
    
    console.print(table)
    
    if not gemini_installed:
        console.print("\n[yellow]To install Gemini CLI:[/yellow]")
        console.print("[dim]pip install gemini-cli[/dim]")
    
    if not google_api_key:
        console.print("\n[yellow]To set Google API key:[/yellow]")
        console.print("[dim]export GOOGLE_API_KEY='your-api-key'[/dim]")
    
    return all(installed for _, installed in checks)


async def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold magenta]cuti Agent System Test Suite[/bold magenta]",
        border_style="cyan"
    ))
    
    # Check installations first
    await test_installation_check()
    
    # Run tests
    tests = [
        ("Claude Agent", test_claude_agent),
        ("Gemini Agent", test_gemini_agent),
        ("Agent Capabilities", test_agent_capabilities),
        ("Multi-Agent Execution", test_multi_agent_execution),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            console.print(f"\n[bold]Running: {test_name}[/bold]")
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            console.print(f"[red]Error in {test_name}: {e}[/red]")
            results.append((test_name, False))
    
    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    
    summary_table = Table()
    summary_table.add_column("Test", style="cyan")
    summary_table.add_column("Result", style="bold")
    
    for test_name, success in results:
        result = "[green]✓ Passed[/green]" if success else "[red]✗ Failed[/red]"
        summary_table.add_row(test_name, result)
    
    console.print(summary_table)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(0)