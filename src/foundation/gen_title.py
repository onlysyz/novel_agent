"""Novel Title Generator.

Generates a compelling novel title based on the seed concept.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client
from src.common.prompts import read_seed, read_language


def generate_title(seed: str = None, language: str = None) -> dict:
    """
    Generate a compelling novel title from the seed concept.

    Returns:
        dict with "title" and "score" keys
    """
    seed = seed or read_seed()
    if not seed:
        raise ValueError("No seed concept provided and seed.txt not found")

    language = language or read_language()

    client = get_client()

    # Language-specific instruction
    lang_instruction = ""
    if language == "zh":
        lang_instruction = "\n\n## Language\nWrite the title in Simplified Chinese."
    elif language == "ja":
        lang_instruction = "\n\n## Language\nWrite the title in Japanese."
    elif language == "ko":
        lang_instruction = "\n\n## Language\nWrite the title in Korean."
    elif language == "es":
        lang_instruction = "\n\n## Language\nWrite the title in Spanish."
    elif language == "fr":
        lang_instruction = "\n\n## Language\nWrite the title in French."
    elif language == "de":
        lang_instruction = "\n\n## Language\nWrite the title in German."

    system = """You are a literary expert specializing in creating compelling novel titles.
A great title should be evocative, memorable, and hint at the story's core themes.
Consider the genre, tone, and central conflict when crafting a title."""

    user = f"""Based on the following novel concept, generate 3 potential titles.
Choose the best one and return only that title (no explanation, no numbering).

## Novel Concept
{seed}
{lang_instruction}

Return ONLY the title, nothing else. The title should be under 10 words."""

    print(f"Generating title for: {seed[:50]}...")

    response = client.generate(system, user, max_tokens=50)
    title = response.strip()

    # Remove quotes if present
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1]
    if title.startswith("'") and title.endswith("'"):
        title = title[1:-1]

    print(f"Generated title: {title}")

    return {"title": title, "score": 8.0}
