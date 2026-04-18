"""World Bible Generator.

Generates a comprehensive world bible from the seed concept.
Includes geography, politics, economy, culture, history, and hard magic systems.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client
from src.common.prompts import build_world_prompt, read_seed, read_layer, read_craft_guide
from src.common.scoring import score_foundation, iteration_summary

DOTNOVEL = Path(".novelforge")
NOVEL_DIR = Path(".")
MIN_SCORE = float(os.getenv("MIN_FOUNDATION_SCORE", "7.0"))
MAX_ITERATIONS = int(os.getenv("MAX_FOUNDATION_ITERATIONS", "15"))


def generate_world(
    seed: str = None,
    voice: str = None,
    craft: str = None,
    min_score: float = MIN_SCORE,
    max_iterations: int = MAX_ITERATIONS,
) -> dict:
    """
    Generate world bible with iterative refinement.

    Args:
        seed: Seed concept (reads from seed.txt if not provided)
        voice: Voice reference for style guidance
        craft: Craft guidelines
        min_score: Minimum score threshold
        max_iterations: Maximum regeneration attempts

    Returns:
        dict with "text", "score", "iterations", and "path" keys
    """
    # Load inputs
    seed = seed or read_seed()
    if not seed:
        raise ValueError("No seed concept provided and seed.txt not found")
    voice = voice or read_layer("voice.md") or None
    craft = craft or read_craft_guide() or None

    client = get_client()
    output_path = NOVEL_DIR / "world.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating world bible for: {seed[:100]}...")
    print(f"Target score: >={min_score}, Max iterations: {max_iterations}")
    print()

    for iteration in range(1, max_iterations + 1):
        print(f"[World Generation] Iteration {iteration}/{max_iterations}")

        system, user = build_world_prompt(seed, voice, craft)

        try:
            text = client.generate(system, user, max_tokens=4096)
        except Exception as e:
            print(f"  API error: {e}")
            if iteration == max_iterations:
                raise
            continue

        # Score the result
        result = score_foundation(text, "world", min_score)
        print(f"  {iteration_summary(iteration, result['score'], result['passed'])}")

        if result["passed"]:
            # Save to file
            output_path.write_text(text)
            print(f"\n✓ World bible generated successfully!")
            print(f"  Saved to: {output_path}")
            print(f"  Final score: {result['score']:.1f}")
            return {
                "text": text,
                "score": result["score"],
                "iterations": iteration,
                "path": str(output_path),
            }
        else:
            # Add refinement context for next iteration
            craft = f"{craft}\n\n## Previous Attempt Feedback\n{result['feedback']}" if craft else result["feedback"]
            print(f"  Refining... (score {result['score']:.1f} < {min_score})")
            print()

    # After max iterations, save best effort
    output_path.write_text(text)
    print(f"\n✗ Max iterations reached. Saved best effort (score: {result['score']:.1f})")
    return {
        "text": text,
        "score": result["score"],
        "iterations": max_iterations,
        "path": str(output_path),
    }


if __name__ == "__main__":
    result = generate_world()
    sys.exit(0 if result["score"] >= MIN_SCORE else 1)
