"""Anthropic API client with caching and error handling."""

import os
import time
import logging
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("novelforge.api")

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
        stream: bool = False,
    ) -> str:
        """Generate text with optional caching and retry logic.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Temperature for generation
            use_cache: Whether to use cached responses
            stream: Whether to use streaming (required for long operations >10min)
        """
        import hashlib

        cache_key = hashlib.sha256(
            f"{self.model}:{system_prompt}:{user_prompt}:{max_tokens}:{temperature}:{stream}".encode()
        ).hexdigest()[:16]
        cache_file = CACHE_DIR / f"{cache_key}.txt"

        if use_cache and cache_file.exists():
            logger.info(f"Cache hit | cache_key={cache_key[:8]} | file={cache_file.name}")
            return cache_file.read_text()

        effective_max_tokens = max_tokens or self.max_tokens
        tokens_multiplier = 1.0  # Track token increase for retry logging

        for attempt in range(3):
            try:
                if stream:
                    # Use streaming for long requests
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=int(effective_max_tokens * tokens_multiplier),
                        temperature=temperature or self.temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        thinking=None,
                        stream=True,
                    )
                    # Handle streaming response
                    text = self._handle_streaming_response(response)
                else:
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=int(effective_max_tokens * tokens_multiplier),
                        temperature=temperature or self.temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        thinking=None,
                    )
                    # Analyze response content blocks (non-streaming)
                    text = self._extract_text_from_response(response)

                if not text:
                    if attempt < 2:
                        old_tokens = int(effective_max_tokens * tokens_multiplier)
                        tokens_multiplier *= 2
                        backoff = (2 ** attempt) + (hash(cache_key) % 10) * 0.1
                        logger.warning(
                            f"Empty response | attempt={attempt + 1}/3 | "
                            f"tokens={int(effective_max_tokens * tokens_multiplier)} (was {old_tokens})"
                        )
                        time.sleep(backoff)
                        continue
                    raise ValueError("Empty response after all retries")

                if use_cache:
                    cache_file.write_text(text)

                logger.info(
                    f"API response success | model={self.model} | "
                    f"tokens={int(effective_max_tokens * tokens_multiplier)} | "
                    f"response_chars={len(text)} | cache_key={cache_key[:8]}"
                )
                return text

            except ValueError:
                raise
            except Exception as e:
                if attempt == 2:
                    logger.error(
                        f"API exhausted retries | attempt={attempt + 1}/3 | "
                        f"error_type={type(e).__name__} | error={str(e)[:100]}"
                    )
                    raise
                backoff = (2 ** attempt) + (hash(cache_key) % 10) * 0.1
                logger.warning(
                    f"API attempt failed | attempt={attempt + 1}/3 | "
                    f"error_type={type(e).__name__} | error={str(e)[:100]} | "
                    f"backoff={backoff:.1f}s"
                )
                print(f"API attempt {attempt + 1} failed: {e}, retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        raise RuntimeError("Should not reach here")

    def _extract_text_from_response(self, response) -> str:
        """Extract text from non-streaming API response."""
        text_parts = []
        thinking_parts = []
        has_text = False

        for block in response.content:
            if hasattr(block, 'type'):
                if block.type == 'text':
                    has_text = True
                    text_parts.append(block.text)
                elif block.type == 'thinking':
                    thinking_parts.append(getattr(block, 'thinking', ''))

        if text_parts:
            return "\n".join(text_parts)
        elif thinking_parts:
            # Fallback to thinking content if no text
            return "\n".join(thinking_parts)
        return ""

    def _handle_streaming_response(self, response) -> str:
        """Extract text from streaming API response."""
        text_parts = []
        thinking_parts = []

        for event in response:
            # Handle content block delta events
            if hasattr(event, 'type') and event.type == 'content_block_delta':
                delta = getattr(event, 'delta', None)
                if delta:
                    if hasattr(delta, 'type'):
                        if delta.type == 'text_delta':
                            text_parts.append(getattr(delta, 'text', ''))
                        elif delta.type == 'thinking_delta':
                            thinking_parts.append(getattr(delta, 'thinking', ''))

        if text_parts:
            return "\n".join(text_parts)
        elif thinking_parts:
            return "\n".join(thinking_parts)
        return ""

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
