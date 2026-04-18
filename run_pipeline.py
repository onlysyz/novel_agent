#!/usr/bin/env python3
"""
NovelForge Pipeline Orchestrator

Orchestrates the complete novel writing pipeline:
1. Foundation Phase - Generate world, characters, outline, canon, voice
2. Drafting Phase - Sequential chapter writing with evaluation
3. Review Phase - Multi-cycle revision with reader panel and Opus review
4. Export Phase - Generate final deliverables

Usage:
    python run_pipeline.py --from-scratch  # Start fresh
    python run_pipeline.py                  # Resume from state
    python run_pipeline.py --phase foundation  # Run specific phase
    python run_pipeline.py --max-cycles 4   # Limit revision cycles
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DOTNOVEL = Path(".novelforge")
NOVEL_DIR = Path(".")
STATE_FILE = DOTNOVEL / "state.json"


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "phase": "foundation",
        "foundation": {},
        "current_chapter": 0,
        "revision_cycles": 0,
    }


def save_state(state):
    DOTNOVEL.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def print_header(text):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def run_foundation(state: dict) -> dict:
    """Generate all planning documents.

    Order: world -> characters -> outline -> canon -> voice
    """
    print_header("FOUNDATION PHASE")

    # Import generators
    sys.path.insert(0, str(NOVEL_DIR))
    from src.foundation import (
        generate_world,
        generate_characters,
        generate_outline,
        generate_canon,
        generate_voice,
    )

    seed_path = NOVEL_DIR / "seed.txt"
    if not seed_path.exists():
        raise FileNotFoundError(
            "seed.txt not found. Create it with your novel concept.\n"
            "Example: echo 'A retired assassin is forced back into service...' > seed.txt"
        )

    seed = seed_path.read_text().strip()
    print(f"Novel concept: {seed[:100]}{'...' if len(seed) > 100 else ''}")
    print()

    foundation_results = {}

    # Step 1: World Bible
    print("[1/5] Generating World Bible...")
    start = time.time()
    result = generate_world(seed=seed)
    foundation_results["world"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "path": result["path"],
    }
    print(f"  Completed in {time.time() - start:.1f}s")
    print()

    # Step 2: Character Profiles
    print("[2/5] Generating Character Profiles...")
    start = time.time()
    world = (NOVEL_DIR / "world.md").read_text()
    result = generate_characters(seed=seed, world=world)
    foundation_results["characters"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "path": result["path"],
    }
    print(f"  Completed in {time.time() - start:.1f}s")
    print()

    # Step 3: Story Outline
    print("[3/5] Generating Story Outline...")
    start = time.time()
    characters = (NOVEL_DIR / "characters.md").read_text()
    result = generate_outline(seed=seed, world=world, characters=characters)
    foundation_results["outline"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "path": result["path"],
    }
    print(f"  Completed in {time.time() - start:.1f}s")
    print()

    # Step 4: Canonical Facts
    print("[4/5] Generating Canonical Facts...")
    start = time.time()
    outline = (NOVEL_DIR / "outline.md").read_text()
    result = generate_canon(seed=seed, world=world, characters=characters, outline=outline)
    foundation_results["canon"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "path": result["path"],
    }
    print(f"  Completed in {time.time() - start:.1f}s")
    print()

    # Step 5: Voice Fingerprint
    print("[5/5] Generating Voice Fingerprint...")
    start = time.time()
    result = generate_voice(seed=seed)
    foundation_results["voice"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "path": result["path"],
    }
    print(f"  Completed in {time.time() - start:.1f}s")
    print()

    # Summary
    print_header("FOUNDATION PHASE COMPLETE")
    print("Generated documents:")
    for name, info in foundation_results.items():
        print(f"  {name:15s} score={info['score']:.1f} iterations={info['iterations']}")
    print()

    return foundation_results


def run_drafting(state: dict):
    """Sequential chapter writing."""
    print_header("DRAFTING PHASE")
    print("Chapter drafting not yet implemented")
    print("Run: python run_pipeline.py --phase review")
    # TODO: Implement chapter drafting
    # - draft_chapter.py -> chapters/ch_NN.md
    # - evaluate.py -> scoring
    # - retry logic (max 5 attempts)


def run_review(state: dict):
    """Multi-cycle revision."""
    print_header("REVIEW PHASE")
    print("Review not yet implemented")
    print("Run: python run_pipeline.py --phase export")
    # TODO: Implement review cycles
    # - adversarial_edit.py
    # - reader_panel.py
    # - review.py (Opus)


def run_export(state: dict):
    """Generate final deliverables."""
    print_header("EXPORT PHASE")
    print("Export not yet implemented")
    # TODO: Implement export
    # - LaTeX typesetting
    # - PDF generation
    # - ePub building


def main():
    parser = argparse.ArgumentParser(description="NovelForge Pipeline")
    parser.add_argument("--from-scratch", action="store_true", help="Start from scratch")
    parser.add_argument(
        "--phase",
        choices=["foundation", "drafting", "review", "export"],
        help="Run specific phase",
    )
    parser.add_argument("--max-cycles", type=int, default=6, help="Max revision cycles")
    parser.add_argument("--seed", type=str, help="Override seed text")
    args = parser.parse_args()

    # Handle seed override
    if args.seed:
        seed_path = NOVEL_DIR / "seed.txt"
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        seed_path.write_text(args.seed)
        print(f"Seed written to {seed_path}")

    if args.from_scratch:
        state = {
            "phase": "foundation",
            "foundation": {},
            "current_chapter": 0,
            "revision_cycles": 0,
        }
        save_state(state)
    else:
        state = load_state()

    phase = args.phase or state.get("phase", "foundation")

    print(f"\nNovelForge Pipeline - {phase.upper()} phase")

    if phase == "foundation":
        foundation_results = run_foundation(state)
        state["foundation"] = foundation_results
        state["phase"] = "drafting"
        save_state(state)
    elif phase == "drafting":
        run_drafting(state)
    elif phase == "review":
        run_review(state)
    elif phase == "export":
        run_export(state)

    print("\nDone!")


if __name__ == "__main__":
    main()
