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
from pathlib import Path

DOTNOVEL = Path(".novelforge")
STATE_FILE = DOTNOVEL / "state.json"


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"phase": "foundation", "current_chapter": 0, "revision_cycles": 0}


def save_state(state):
    DOTNOVEL.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run_foundation():
    """Generate all planning documents."""
    print("=== Foundation Phase ===")
    # TODO: Implement foundation generation
    # - gen_world.py -> world.md
    # - gen_characters.py -> characters.md
    # - gen_outline.py -> outline.md
    # - gen_canon.py -> canon.md
    # - voice_fingerprint.py -> voice.md
    print("Foundation phase not yet implemented")


def run_drafting():
    """Sequential chapter writing."""
    print("=== Drafting Phase ===")
    # TODO: Implement chapter drafting
    # - draft_chapter.py -> chapters/ch_NN.md
    # - evaluate.py -> scoring
    # - retry logic (max 5 attempts)
    print("Drafting phase not yet implemented")


def run_review():
    """Multi-cycle revision."""
    print("=== Review Phase ===")
    # TODO: Implement review cycles
    # - adversarial_edit.py
    # - reader_panel.py
    # - review.py (Opus)
    print("Review phase not yet implemented")


def run_export():
    """Generate final deliverables."""
    print("=== Export Phase ===")
    # TODO: Implement export
    # - LaTeX typesetting
    # - PDF generation
    # - ePub building
    print("Export phase not yet implemented")


def main():
    parser = argparse.ArgumentParser(description="NovelForge Pipeline")
    parser.add_argument("--from-scratch", action="store_true", help="Start from scratch")
    parser.add_argument("--phase", choices=["foundation", "drafting", "review", "export"], help="Run specific phase")
    parser.add_argument("--max-cycles", type=int, default=6, help="Max revision cycles")
    args = parser.parse_args()

    if args.from_scratch:
        state = {"phase": "foundation", "current_chapter": 0, "revision_cycles": 0}
        save_state(state)
    else:
        state = load_state()

    phase = args.phase or state.get("phase", "foundation")

    if phase == "foundation":
        run_foundation()
    elif phase == "drafting":
        run_drafting()
    elif phase == "review":
        run_review()
    elif phase == "export":
        run_export()


if __name__ == "__main__":
    main()
