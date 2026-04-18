"""Voice Fingerprint Generator.

Analyzes sample texts to extract the author's writing style voice.
Generates a prescriptive voice.md that writer agents should follow.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client
from src.common.prompts import build_voice_prompt, read_seed
from src.common.scoring import score_foundation, iteration_summary

DOTNOVEL = Path(".novelforge")
NOVEL_DIR = Path(".")
MIN_SCORE = float(os.getenv("MIN_FOUNDATION_SCORE", "7.0"))
MAX_ITERATIONS = int(os.getenv("MAX_FOUNDATION_ITERATIONS", "10"))

# Default sample texts for when user hasn't provided any
DEFAULT_SAMPLES = [
    """The rain came down in sheets, each drop a small percussion against the windows. She watched the street below, the neon signs reflecting in puddles like drowned advertisements. A car passed, its headlights cutting through the gray evening, and for a moment she saw her own face in the rear window - older than she remembered, tired in ways sleep couldn't fix.

"There's no such thing as a clean exit," she said to no one. The coffee had gone cold hours ago.""",

    """He found the letter on a Tuesday, which felt wrong somehow. Important things happened on Tuesdays in books - revelations, betrayals, the kind of twists that changed everything. But this was just a Tuesday in October, the light outside turning golden and thin, and the letter was sitting on the kitchen counter like it had always been there.

Three pages. His mother's handwriting. The kind of writing that slanted hard to the right, as if the words were trying to escape the page.""",
]


def generate_voice(
    seed: str = None,
    sample_texts: list = None,
    min_score: float = MIN_SCORE,
    max_iterations: int = MAX_ITERATIONS,
) -> dict:
    """
    Generate voice fingerprint from sample texts.

    Args:
        seed: Seed concept (reads from seed.txt if not provided)
        sample_texts: List of sample texts (reads from voice_samples/ dir if not provided)
        min_score: Minimum score threshold
        max_iterations: Maximum regeneration attempts

    Returns:
        dict with "text", "score", "iterations", and "path" keys
    """
    # Load seed
    seed = seed or read_seed()
    if not seed:
        raise ValueError("No seed concept provided and seed.txt not found")

    # Load sample texts
    if sample_texts is None:
        # Try to load from voice_samples directory
        samples_dir = NOVEL_DIR / "voice_samples"
        if samples_dir.exists():
            sample_files = sorted(samples_dir.glob("*.txt"))
            if sample_files:
                sample_texts = [f.read_text().strip() for f in sample_files]
        if not sample_texts:
            # Try voice.md as sample (if it exists with actual prose)
            existing_voice = (NOVEL_DIR / "voice.md").read_text().strip() if (NOVEL_DIR / "voice.md").exists() else ""
            if existing_voice and len(existing_voice) > 500:
                sample_texts = [existing_voice[:2000]]
            else:
                sample_texts = DEFAULT_SAMPLES

    client = get_client()
    output_path = NOVEL_DIR / "voice.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating voice fingerprint from {len(sample_texts)} sample(s)...")
    print(f"Target score: >={min_score}, Max iterations: {max_iterations}")
    print()

    refinement_context = None

    for iteration in range(1, max_iterations + 1):
        print(f"[Voice Generation] Iteration {iteration}/{max_iterations}")

        system, user = build_voice_prompt(sample_texts, seed)

        if refinement_context:
            user += f"\n\n## Previous Attempt Feedback\n{refinement_context}"

        try:
            text = client.generate(system, user, max_tokens=4096)
        except Exception as e:
            print(f"  API error: {e}")
            if iteration == max_iterations:
                raise
            continue

        # Score the result
        result = score_foundation(text, "voice", min_score)
        print(f"  {iteration_summary(iteration, result['score'], result['passed'])}")

        if result["passed"]:
            output_path.write_text(text)
            print(f"\n✓ Voice fingerprint generated successfully!")
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
    result = generate_voice()
    sys.exit(0 if result["score"] >= MIN_SCORE else 1)
