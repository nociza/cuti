"""
Interface for executing prompts via Claude Code CLI.
"""

import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple

from .models import ExecutionResult, RateLimitInfo, QueuedPrompt


class ClaudeCodeInterface:
    """Interface for executing prompts via Claude Code CLI."""

    def __init__(self, claude_command: str = "claude", timeout: int = 3600):
        self.claude_command = claude_command
        self.timeout = timeout
        self._verify_claude_available()

    def _verify_claude_available(self) -> None:
        """Verify Claude Code CLI is available."""
        try:
            result = subprocess.run(
                [self.claude_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Claude Code CLI not available: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                f"Claude Code CLI not found. Make sure '{self.claude_command}' is in PATH."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code CLI verification timed out.")

    def execute_prompt(self, prompt: QueuedPrompt) -> ExecutionResult:
        """Execute a prompt via Claude Code CLI."""
        start_time = time.time()

        try:
            original_cwd = os.getcwd()

            working_dir = Path(prompt.working_directory).resolve()
            if not working_dir.exists():
                working_dir.mkdir(parents=True, exist_ok=True)

            os.chdir(working_dir)

            cmd = [
                self.claude_command,
                "--print",
                "--dangerously-skip-permissions",
            ]  # Use --print for non-interactive output and skip permissions

            full_prompt = prompt.content

            if prompt.context_files:
                context_refs = []
                for context_file in prompt.context_files:
                    context_path = Path(context_file)  # Relative to working directory
                    if context_path.exists():
                        context_refs.append(f"@{context_file}")

                if context_refs:
                    full_prompt = f"{' '.join(context_refs)} {prompt.content}"

            cmd.append(full_prompt)

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout
            )

            os.chdir(original_cwd)

            execution_time = time.time() - start_time

            rate_limit_info = self._detect_rate_limit(result.stdout + result.stderr)

            success = result.returncode == 0 and not rate_limit_info.is_rate_limited

            return ExecutionResult(
                success=success,
                output=result.stdout,
                error=result.stderr,
                rate_limit_info=rate_limit_info,
                execution_time=execution_time,
            )

        except subprocess.TimeoutExpired:
            try:
                os.chdir(original_cwd)
            except:
                pass
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.timeout} seconds",
                execution_time=execution_time,
            )
        except Exception as e:
            try:
                os.chdir(original_cwd)
            except:
                pass
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                execution_time=execution_time,
            )

    def _detect_rate_limit(self, output: str) -> RateLimitInfo:
        """Detect rate limiting from Claude Code output."""
        output_lower = output.lower()

        # Common rate limit patterns
        rate_limit_patterns = [
            ("usage limit reached", self._extract_reset_time_from_limit_message),
            ("rate limit exceeded", self._estimate_reset_time),
            ("too many requests", self._estimate_reset_time),
            ("quota exceeded", self._estimate_reset_time),
            ("limit exceeded", self._estimate_reset_time),
        ]

        for pattern, reset_extractor in rate_limit_patterns:
            if pattern in output_lower:
                reset_time = reset_extractor(output)
                return RateLimitInfo(
                    is_rate_limited=True,
                    reset_time=reset_time,
                    limit_message=output.strip()[:500],  # First 500 chars
                    timestamp=datetime.now(),
                )

        return RateLimitInfo(is_rate_limited=False)

    def _extract_reset_time_from_limit_message(self, output: str) -> Optional[datetime]:
        """Extract reset time from Claude's limit message."""
        try:
            import re
            from zoneinfo import ZoneInfo

            # Pattern 1: "Your limit will reset at 9pm (America/New_York)"
            pattern_reset = r"limit will reset at (\d{1,2}(?::\d{2})?)\s*([ap]m)\s*\(([^)]+)\)"
            match_reset = re.search(pattern_reset, output, re.IGNORECASE)
            if match_reset:
                time_str = match_reset.group(1)
                am_pm = match_reset.group(2).lower()
                timezone_str = match_reset.group(3)
                
                # Parse the time
                if ':' in time_str:
                    hour, minute = map(int, time_str.split(':'))
                else:
                    hour = int(time_str)
                    minute = 0
                
                # Convert to 24-hour format
                if am_pm == 'pm' and hour != 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
                
                # Get current time in the specified timezone
                try:
                    tz = ZoneInfo(timezone_str)
                    now_tz = datetime.now(tz)
                    
                    # Create reset time for today
                    reset_time = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If reset time is in the past, it must be tomorrow
                    if reset_time <= now_tz:
                        reset_time += timedelta(days=1)
                    
                    # Convert to local timezone
                    return reset_time.astimezone()
                except Exception:
                    # Fallback: assume EST/EDT
                    from datetime import timezone
                    now = datetime.now()
                    reset_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if reset_time <= now:
                        reset_time += timedelta(days=1)
                    return reset_time

            # Pattern 2: Unix timestamp format
            pattern1 = r"usage limit reached\|(\d+)"
            match1 = re.search(pattern1, output, re.IGNORECASE)
            if match1:
                timestamp = int(match1.group(1))
                return datetime.fromtimestamp(timestamp)

            # Pattern 3: ISO format timestamps
            pattern2 = (
                r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
            )
            matches = re.findall(pattern2, output)
            if matches:
                latest_time = None
                for match in matches:
                    try:
                        if match.endswith("Z"):
                            ts = datetime.fromisoformat(match.replace("Z", "+00:00"))
                        else:
                            ts = datetime.fromisoformat(match)

                        if latest_time is None or ts > latest_time:
                            latest_time = ts
                    except ValueError:
                        continue

                if latest_time:
                    return latest_time + timedelta(hours=5)

        except Exception as e:
            print(f"Error parsing reset time: {e}")

        return self._estimate_reset_time(output)

    def _estimate_reset_time(self, output: str) -> datetime:
        """Estimate reset time based on Claude's 5-hour windows."""
        now = datetime.now()

        hour = now.hour
        if hour < 5:
            next_reset = now.replace(hour=5, minute=0, second=0, microsecond=0)
        elif hour < 10:
            next_reset = now.replace(hour=10, minute=0, second=0, microsecond=0)
        elif hour < 15:
            next_reset = now.replace(hour=15, minute=0, second=0, microsecond=0)
        elif hour < 20:
            next_reset = now.replace(hour=20, minute=0, second=0, microsecond=0)
        else:
            next_reset = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        if next_reset <= now:
            next_reset += timedelta(hours=5)

        return next_reset

    def test_connection(self) -> Tuple[bool, str]:
        """Test if Claude Code is working."""
        try:
            result = subprocess.run(
                [self.claude_command, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return True, "Claude Code CLI is working"
            else:
                return False, f"Claude Code CLI error: {result.stderr}"

        except FileNotFoundError:
            return False, f"Claude Code CLI not found: {self.claude_command}"
        except subprocess.TimeoutExpired:
            return False, "Claude Code CLI test timed out"
        except Exception as e:
            return False, f"Claude Code CLI test failed: {str(e)}"

    def get_available_commands(self) -> List[str]:
        """Get available Claude Code commands."""
        try:
            result = subprocess.run(
                [self.claude_command, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                lines = result.stdout.split("\n")
                commands = []
                in_commands_section = False

                for line in lines:
                    if "commands:" in line.lower() or "usage:" in line.lower():
                        in_commands_section = True
                        continue

                    if in_commands_section and line.strip():
                        if line.startswith("  "):
                            cmd = line.strip().split()[0]
                            if cmd and not cmd.startswith("-"):
                                commands.append(cmd)

                return commands

        except Exception as e:
            print(f"Error getting available commands: {e}")

        return []

    def execute_simple_prompt(
        self, prompt_text: str, working_dir: str = "."
    ) -> ExecutionResult:
        """Execute a simple prompt without full QueuedPrompt object."""
        simple_prompt = QueuedPrompt(content=prompt_text, working_directory=working_dir)
        return self.execute_prompt(simple_prompt)
    
    async def stream_prompt(self, prompt_text: str, working_dir: str = "."):
        """Stream output from Claude Code CLI asynchronously."""
        import asyncio
        
        # Prepare command
        cmd = [
            self.claude_command,
            prompt_text
        ]
        
        try:
            # Change to working directory
            original_cwd = os.getcwd()
            working_path = Path(working_dir).resolve()
            if not working_path.exists():
                working_path.mkdir(parents=True, exist_ok=True)
            os.chdir(working_path)
            
            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ}
            )
            
            # Stream stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8', errors='replace')
            
            # Wait for process to complete
            await process.wait()
            
            # Change back to original directory
            os.chdir(original_cwd)
            
            # If there's stderr, yield it
            if process.returncode != 0:
                stderr = await process.stderr.read()
                if stderr:
                    yield f"\n[Error] {stderr.decode('utf-8', errors='replace')}"
                    
        except Exception as e:
            # Ensure we change back to original directory
            try:
                os.chdir(original_cwd)
            except:
                pass
            yield f"\n[Error] {str(e)}"
