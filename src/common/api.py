"""Anthropic API client with caching and error handling."""

import os
import time
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Cache for API responses (keyed by content hash)
CACHE_DIR = Path(".novelforge/.cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class AnthropicClient:
    """Wrapper around Anthropic API with retry logic and caching."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        temperature: float = 0.5,
    ):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
    ) -> str:
        """Generate text with optional caching and retry logic."""
        import hashlib

        cache_key = hashlib.sha256(
            f"{self.model}:{system_prompt}:{user_prompt}:{max_tokens}:{temperature}".encode()
        ).hexdigest()[:16]
        cache_file = CACHE_DIR / f"{cache_key}.txt"

        if use_cache and cache_file.exists():
            return cache_file.read_text()

        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=temperature or self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    # Disable extended thinking to prevent ThinkingBlock returns
                    thinking=None,
                )

                # Handle different content block types (TextBlock, ThinkingBlock)
                text_parts = []
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'text':
                        text_parts.append(block.text)
                    elif hasattr(block, 'thinking') and block.thinking:
                        # Fallback: extract thinking content if text is empty
                        # (edge case when API still returns thinking despite disable)
                        pass
                text = "\n".join(text_parts)

                if not text:
                    raise ValueError(f"No text content in response. Content: {response.content}")

                if use_cache:
                    cache_file.write_text(text)

                return text

            except Exception as e:
                if attempt == 2:
                    raise
                print(f"API attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(2 ** attempt)

        raise RuntimeError("Should not reach here")

    def generate_with_opus(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate using Opus model (for review tasks)."""
        original_model = self.model
        try:
            self.model = os.getenv("CLAUDE_OPUS_MODEL", "opus-4-5-20251114")
            return self.generate(system_prompt, user_prompt, max_tokens)
        finally:
            self.model = original_model


def get_client(model: Optional[str] = None) -> AnthropicClient:
    """Get or create an AnthropicClient instance."""
    return AnthropicClient(model=model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"))
