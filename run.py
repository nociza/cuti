#!/usr/bin/env python3
"""
Main entry point for ccutils.
Supports both uvx and direct execution.
"""

import sys
import os
from pathlib import Path
import subprocess
import argparse


def check_uv_available():
    """Check if uv is available."""
    try:
        result = subprocess.run(['uv', '--version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_with_uv():
    """Install the package with uv in development mode."""
    try:
        print("Installing ccutils with uv...")
        result = subprocess.run(['uv', 'pip', 'install', '-e', '.'], 
                              check=True, cwd=Path(__file__).parent)
        print("✓ Installation completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation failed: {e}")
        return False


def setup_environment():
    """Set up the development environment."""
    project_root = Path(__file__).parent
    
    # Check if we're in a virtual environment or can create one
    if not check_uv_available():
        print("❌ uv is not available. Please install uv first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("   or visit: https://docs.astral.sh/uv/getting-started/installation/")
        return False
    
    # Install the package
    if not install_with_uv():
        return False
    
    # Create default configuration directory
    config_dir = Path.home() / '.claude-queue'
    config_dir.mkdir(exist_ok=True)
    
    print(f"✓ Configuration directory created: {config_dir}")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ccutils - Production-ready queue system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set up the environment
  python run.py setup
  
  # Start the web interface
  python run.py web
  
  # Start the CLI
  python run.py cli
  
  # Start queue processor
  python run.py start
  
  # Show status
  python run.py status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Set up the environment')
    
    # Web command
    web_parser = subparsers.add_parser('web', help='Start web interface')
    web_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    web_parser.add_argument('--storage-dir', default='~/.claude-queue', help='Storage directory')
    
    # CLI command
    cli_parser = subparsers.add_parser('cli', help='Start CLI interface')
    cli_parser.add_argument('cli_args', nargs='*', help='CLI arguments to pass through')
    
    # Direct queue commands
    start_parser = subparsers.add_parser('start', help='Start queue processor')
    start_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    start_parser.add_argument('--storage-dir', default='~/.claude-queue', help='Storage directory')
    
    status_parser = subparsers.add_parser('status', help='Show queue status')
    status_parser.add_argument('--storage-dir', default='~/.claude-queue', help='Storage directory')
    status_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Add prompt command
    add_parser = subparsers.add_parser('add', help='Add prompt to queue')
    add_parser.add_argument('prompt', help='Prompt text or alias')
    add_parser.add_argument('--priority', '-p', type=int, default=0, help='Priority')
    add_parser.add_argument('--storage-dir', default='~/.claude-queue', help='Storage directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle setup command
    if args.command == 'setup':
        success = setup_environment()
        return 0 if success else 1
    
    # For other commands, ensure the package is importable
    try:
        # Add the src directory to Python path
        src_path = Path(__file__).parent / 'src'
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        # Try importing the package
        import claude_code_queue
        
    except ImportError:
        print("❌ ccutils not installed. Run: python run.py setup")
        return 1
    
    # Handle web command
    if args.command == 'web':
        try:
            from claude_code_queue.web.main import create_app
            import uvicorn
            
            app = create_app(args.storage_dir)
            print(f"🚀 Starting web interface at http://{args.host}:{args.port}")
            print(f"📁 Storage directory: {args.storage_dir}")
            print("Press Ctrl+C to stop")
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            
        except ImportError as e:
            print(f"❌ Web dependencies not available: {e}")
            print("Run: python run.py setup")
            return 1
        except KeyboardInterrupt:
            print("\n👋 Web interface stopped")
            return 0
    
    # Handle CLI command
    elif args.command == 'cli':
        try:
            from claude_code_queue.cli import app as cli_app
            
            # Pass through CLI arguments
            if args.cli_args:
                sys.argv = ['claude-queue'] + args.cli_args
            else:
                sys.argv = ['claude-queue', '--help']
                
            cli_app()
            
        except ImportError as e:
            print(f"❌ CLI not available: {e}")
            print("Run: python run.py setup")
            return 1
    
    # Handle direct queue commands
    else:
        try:
            from claude_code_queue.queue_manager import QueueManager
            from claude_code_queue.models import QueuedPrompt
            from claude_code_queue.aliases import PromptAliasManager
            
            manager = QueueManager(storage_dir=args.storage_dir)
            
            if args.command == 'start':
                print("🚀 Starting ccutils processor...")
                print(f"📁 Storage directory: {args.storage_dir}")
                print("Press Ctrl+C to stop")
                
                def status_callback(state):
                    if args.verbose:
                        stats = state.get_stats()
                        print(f"📊 Queue status: {stats['status_counts']}")
                
                try:
                    manager.start(callback=status_callback if args.verbose else None)
                except KeyboardInterrupt:
                    print("\n👋 Queue processor stopped")
                    return 0
            
            elif args.command == 'status':
                state = manager.get_status()
                stats = state.get_stats()
                
                if args.json:
                    import json
                    print(json.dumps(stats, indent=2))
                else:
                    print("📊 ccutils Status")
                    print("=" * 40)
                    print(f"📝 Total prompts: {stats['total_prompts']}")
                    print(f"✅ Completed: {stats['total_processed']}")
                    print(f"❌ Failed: {stats['failed_count']}")
                    print(f"⚠️  Rate limited: {stats['rate_limited_count']}")
                    
                    print("\n📈 Status breakdown:")
                    for status, count in stats["status_counts"].items():
                        if count > 0:
                            emoji = {
                                "queued": "⏳",
                                "executing": "▶️", 
                                "completed": "✅",
                                "failed": "❌",
                                "cancelled": "🚫",
                                "rate_limited": "⚠️"
                            }.get(status, "❓")
                            print(f"  {emoji} {status}: {count}")
            
            elif args.command == 'add':
                alias_manager = PromptAliasManager(args.storage_dir)
                
                # Resolve alias if needed
                resolved_prompt = alias_manager.resolve_alias(args.prompt)
                if resolved_prompt != args.prompt:
                    print(f"🔗 Using alias: {args.prompt}")
                
                queued_prompt = QueuedPrompt(
                    content=resolved_prompt,
                    priority=args.priority
                )
                
                success = manager.add_prompt(queued_prompt)
                if success:
                    print(f"✅ Added prompt {queued_prompt.id} to queue")
                else:
                    print("❌ Failed to add prompt")
                    return 1
                    
        except ImportError as e:
            print(f"❌ Required components not available: {e}")
            print("Run: python run.py setup")
            return 1
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())