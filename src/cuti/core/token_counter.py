"""
Real-time token counting for Claude interactions.
Provides accurate token estimates for input and output.
"""

import re
from typing import Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TokenMetrics:
    """Token usage metrics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        self.total_tokens = self.input_tokens + self.output_tokens
        self.total_cost = self.input_cost + self.output_cost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": round(self.input_cost, 6),
            "output_cost": round(self.output_cost, 6),
            "total_cost": round(self.total_cost, 6),
            "timestamp": self.timestamp
        }


class TokenCounter:
    """
    Real-time token counter for Claude interactions.
    Uses Claude's tokenization rules for accurate estimates.
    """
    
    # Claude 3.5 Sonnet pricing (as of 2024)
    PRICING = {
        "claude-3-5-sonnet": {
            "input": 3.00 / 1_000_000,   # $3 per million input tokens
            "output": 15.00 / 1_000_000,  # $15 per million output tokens
        },
        "claude-3-opus": {
            "input": 15.00 / 1_000_000,   # $15 per million input tokens
            "output": 75.00 / 1_000_000,  # $75 per million output tokens
        },
        "claude-3-haiku": {
            "input": 0.25 / 1_000_000,    # $0.25 per million input tokens
            "output": 1.25 / 1_000_000,   # $1.25 per million output tokens
        }
    }
    
    def __init__(self, model: str = "claude-3-5-sonnet"):
        """Initialize token counter with model pricing."""
        self.model = model
        self.pricing = self.PRICING.get(model, self.PRICING["claude-3-5-sonnet"])
        self.current_input_tokens = 0
        self.current_output_tokens = 0
        self.session_total_input = 0
        self.session_total_output = 0
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a given text.
        Claude uses a BPE tokenizer similar to GPT models.
        
        This is an approximation based on:
        - Average of ~4 characters per token for English
        - Adjustments for code, punctuation, and special characters
        """
        if not text:
            return 0
        
        # Basic character count
        char_count = len(text)
        
        # Count different types of content
        word_count = len(text.split())
        
        # Code tends to have more tokens due to syntax
        code_patterns = [
            r'\b(def|class|import|function|const|let|var|if|else|for|while)\b',
            r'[{}\[\]()<>]',
            r'[=+\-*/]',
        ]
        code_matches = sum(len(re.findall(pattern, text)) for pattern in code_patterns)
        
        # URLs and paths have more tokens
        url_pattern = r'https?://[^\s]+'
        path_pattern = r'/[\w/\-\.]+'
        special_matches = len(re.findall(url_pattern, text)) + len(re.findall(path_pattern, text))
        
        # Base estimate: characters / 4
        base_tokens = char_count / 4
        
        # Adjustments
        if code_matches > 10:
            # Code has ~3.5 chars per token
            base_tokens = char_count / 3.5
        
        # Add tokens for special patterns
        base_tokens += special_matches * 2
        
        # Minimum of word count (each word is at least 1 token)
        estimated_tokens = max(word_count, int(base_tokens))
        
        return estimated_tokens
    
    def count_prompt_tokens(self, prompt: str, context_files: list = None) -> int:
        """Count tokens in the input prompt including context."""
        total_tokens = self.estimate_tokens(prompt)
        
        # Add tokens for context files
        if context_files:
            for file_content in context_files:
                if isinstance(file_content, str):
                    total_tokens += self.estimate_tokens(file_content)
                    # Add overhead for file reference
                    total_tokens += 10  # Approximate overhead per file
        
        # Add system prompt overhead (approximately)
        total_tokens += 100  # Base system instructions
        
        self.current_input_tokens = total_tokens
        self.session_total_input += total_tokens
        
        return total_tokens
    
    def count_streaming_tokens(self, text_chunk: str) -> Tuple[int, int]:
        """
        Count tokens in a streaming text chunk.
        Returns (chunk_tokens, cumulative_output_tokens).
        """
        chunk_tokens = self.estimate_tokens(text_chunk)
        self.current_output_tokens += chunk_tokens
        self.session_total_output += chunk_tokens
        
        return chunk_tokens, self.current_output_tokens
    
    def get_current_metrics(self) -> TokenMetrics:
        """Get current token metrics with costs."""
        return TokenMetrics(
            input_tokens=self.current_input_tokens,
            output_tokens=self.current_output_tokens,
            input_cost=self.current_input_tokens * self.pricing["input"],
            output_cost=self.current_output_tokens * self.pricing["output"]
        )
    
    def get_session_metrics(self) -> TokenMetrics:
        """Get session total metrics."""
        return TokenMetrics(
            input_tokens=self.session_total_input,
            output_tokens=self.session_total_output,
            input_cost=self.session_total_input * self.pricing["input"],
            output_cost=self.session_total_output * self.pricing["output"]
        )
    
    def reset_current(self):
        """Reset current conversation metrics."""
        self.current_input_tokens = 0
        self.current_output_tokens = 0
    
    def format_cost(self, cost: float) -> str:
        """Format cost for display."""
        if cost < 0.01:
            return f"${cost:.4f}"
        elif cost < 1:
            return f"${cost:.3f}"
        else:
            return f"${cost:.2f}"
    
    def get_token_rate(self, tokens: int, duration_seconds: float) -> float:
        """Calculate tokens per second rate."""
        if duration_seconds <= 0:
            return 0
        return tokens / duration_seconds
    
    def estimate_completion_time(self, estimated_total_tokens: int, current_rate: float) -> float:
        """Estimate time to completion based on current rate."""
        if current_rate <= 0:
            return 0
        remaining_tokens = max(0, estimated_total_tokens - self.current_output_tokens)
        return remaining_tokens / current_rate