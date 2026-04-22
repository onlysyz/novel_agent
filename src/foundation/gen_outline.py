"""Story Outline Generator.

Generates a complete story outline with Save the Cat beats, foreshadowing ledger,
character arcs, and chapter-by-chapter breakdown.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client
from src.common.prompts import build_outline_prompt, read_seed, read_layer, read_language
from src.common.scoring import score_foundation, iteration_summary
from src.common.constants import get_foundation_config

DOTNOVEL = Path(".novelforge")
NOVEL_DIR = Path(".")

config = get_foundation_config("outline")
MIN_SCORE = float(os.getenv("MIN_FOUNDATION_SCORE", str(config["min_score"])))
MAX_ITERATIONS = int(os.getenv("MAX_FOUNDATION_ITERATIONS", str(config["max_iterations"])))


def generate_outline(
    seed: str = None,
    world: str = None,
    characters: str = None,
    voice: str = None,
    language: str = None,
    min_score: float = MIN_SCORE,
    max_iterations: int = MAX_ITERATIONS,
) -> dict:
    """
    Generate story outline with iterative refinement.

    Args:
        seed: Seed concept (reads from seed.txt if not provided)
        world: World bible (reads from world.md if not provided)
        characters: Character profiles (reads from characters.md if not provided)
        voice: Voice reference for style guidance
        language: Language code (reads from seed.txt if not provided)
        min_score: Minimum score threshold
        max_iterations: Maximum regeneration attempts

    Returns:
        dict with "text", "score", "iterations", and "path" keys
    """
    # Load inputs
    seed = seed or read_seed()
    if not seed:
        raise ValueError("No seed concept provided and seed.txt not found")
    world = world or read_layer("world.md")
    if not world:
        raise ValueError("No world bible provided and world.md not found")
    characters = characters or read_layer("characters.md")
    if not characters:
        raise ValueError("No character profiles provided and characters.md not found")
    voice = voice or read_layer("voice.md") or None
    language = language or read_language()

    client = get_client()
    output_path = NOVEL_DIR / "outline.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine chapter count from env
    chapter_target = int(os.getenv("CHAPTER_TARGET", "22"))

    print(f"Generating story outline ({chapter_target} chapters)...")
    print(f"Target score: >={min_score}, Max iterations: {max_iterations}")
    print()

    refinement_context = None

    for iteration in range(1, max_iterations + 1):
        print(f"[Outline Generation] Iteration {iteration}/{max_iterations}")

        system, user = build_outline_prompt(seed, world, characters, voice, language=language)

        if refinement_context:
            user += f"\n\n## Previous Attempt Feedback\n{refinement_context}"

        try:
            text = client.generate(system, user, max_tokens=8192)
        except Exception as e:
            print(f"  API error: {e}")
            if iteration == max_iterations:
                raise
            continue

        # Score the result
        result = score_foundation(text, "outline", min_score)
        print(f"  {iteration_summary(iteration, result['score'], result['passed'])}")

        if result["passed"]:
            output_path.write_text(text)
            print(f"\n✓ Story outline generated successfully!")
            print(f"  Saved to: {output_path}")
            print(f"  Final score: {result['score']:.1f}")
            return {
                "text": text,
                "score": result["score"],
                "iterations": iteration,
                "path": str(output_path),
            }
        else:
            refinement_context = result["feedback"]
            print(f"  Refining... (score {result['score']:.1f} < {min_score})")
            print()

    output_path.write_text(text)
    print(f"\n✗ Max iterations reached. Saved best effort (score: {result['score']:.1f})")
    return {
        "text": text,
        "score": result["score"],
        "iterations": max_iterations,
        "path": str(output_path),
    }


if __name__ == "__main__":
    result = generate_outline()
    sys.exit(0 if result["score"] >= MIN_SCORE else 1)
