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
    ) -> str:
        """Generate text with optional caching and retry logic."""
        import hashlib

        cache_key = hashlib.sha256(
            f"{self.model}:{system_prompt}:{user_prompt}:{max_tokens}:{temperature}".encode()
        ).hexdigest()[:16]
        cache_file = CACHE_DIR / f"{cache_key}.txt"

        if use_cache and cache_file.exists():
            logger.info(f"Cache hit | cache_key={cache_key[:8]} | file={cache_file.name}")
            return cache_file.read_text()

        effective_max_tokens = max_tokens or self.max_tokens
        tokens_multiplier = 1.0  # Track token increase for retry logging

        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=int(effective_max_tokens * tokens_multiplier),
                    temperature=temperature or self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    # Disable extended thinking to prevent ThinkingBlock returns
                    thinking=None,
                )

                # Analyze response content blocks
                text_parts = []
                thinking_blocks = []
                has_text_block = False
                has_thinking_block = False

                for block in response.content:
                    if hasattr(block, 'type'):
                        if block.type == 'text':
                            has_text_block = True
                            text_parts.append(block.text)
                        elif block.type == 'thinking':
                            has_thinking_block = True
                            # ThinkingBlock has a 'thinking' attribute with the content
                            thinking_blocks.append(getattr(block, 'thinking', ''))

                text = "\n".join(text_parts) if text_parts else ""

                # Detect ThinkingBlock-only response (model ran out of tokens for actual response)
                if has_thinking_block and not has_text_block and text_parts:
                    # This shouldn't happen with thinking=None, but handle it
                    text = "\n".join(thinking_blocks)

                # Check for ThinkingBlock-only response where we fell back to thinking content
                thinking_only_response = has_thinking_block and not has_text_block and not text_parts

                if not text or thinking_only_response:
                    # Response contains only ThinkingBlock - model ran out of space
                    if attempt < 2:
                        old_tokens = int(effective_max_tokens * tokens_multiplier)
                        tokens_multiplier *= 2  # Double tokens for next attempt
                        backoff = (2 ** attempt) + (hash(cache_key) % 10) * 0.1  # Exponential + jitter
                        logger.warning(
                            "ThinkingBlock-only response | "
                            f"attempt={attempt + 1}/3 | "
                            f"tokens={int(effective_max_tokens * tokens_multiplier)} "
                            f"(was {old_tokens}) | "
                            f"backoff={backoff:.1f}s | "
                            f"cache_key={cache_key[:8]}"
                        )
                        print(f"  [API] ThinkingBlock-only response, retrying with {int(effective_max_tokens * tokens_multiplier)} tokens (was {old_tokens}), backoff: {backoff:.1f}s")
                        time.sleep(backoff)
                        continue
                    else:
                        # Last attempt: extract what we can from thinking blocks
                        thinking_content = "\n".join(thinking_blocks) if thinking_blocks else ""
                        if thinking_content:
                            logger.warning(
                                f"Using thinking content as fallback | "
                                f"chars={len(thinking_content)} | "
                                f"cache_key={cache_key[:8]}"
                            )
                            print(f"  [API] Warning: Returning thinking content as fallback ({len(thinking_content)} chars)")
                            if use_cache:
                                cache_file.write_text(thinking_content)
                            return thinking_content
                        logger.error(
                            f"No text content in response | "
                            f"cache_key={cache_key[:8]} | "
                            f"content_blocks={len(response.content)}"
                        )
                        raise ValueError(f"No text content in response. Content: {response.content}")

                if use_cache:
                    cache_file.write_text(text)

                logger.info(
                    f"API response success | "
                    f"model={self.model} | "
                    f"tokens={int(effective_max_tokens * tokens_multiplier)} | "
                    f"response_chars={len(text)} | "
                    f"cache_key={cache_key[:8]}"
                )
                return text

            except ValueError:
                raise
            except Exception as e:
                if attempt == 2:
                    logger.error(
                        f"API exhausted retries | "
                        f"attempt={attempt + 1}/3 | "
                        f"error_type={type(e).__name__} | "
                        f"error={str(e)[:100]} | "
                        f"cache_key={cache_key[:8]}"
                    )
                    raise
                backoff = (2 ** attempt) + (hash(cache_key) % 10) * 0.1  # Exponential + jitter
                logger.warning(
                    f"API attempt failed | "
                    f"attempt={attempt + 1}/3 | "
                    f"error_type={type(e).__name__} | "
                    f"error={str(e)[:100]} | "
                    f"backoff={backoff:.1f}s | "
                    f"cache_key={cache_key[:8]}"
                )
                print(f"API attempt {attempt + 1} failed: {e}, retrying in {backoff:.1f}s...")
                time.sleep(backoff)

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
