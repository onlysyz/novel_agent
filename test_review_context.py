#!/usr/bin/env python3
"""Test script for review phase with proper context package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.review.review import opus_review
from src.drafting.draft_chapter import build_context_package

NOVEL_DIR = Path(".")


def test_review_phase():
    """Test review on chapters 1-3 with proper context."""

    for chapter_num in range(1, 4):
        print(f"\n{'='*60}")
        print(f"REVIEWING CHAPTER {chapter_num}")
        print('='*60)

        chapter_path = NOVEL_DIR / "chapters" / f"ch_{chapter_num:02d}.md"
        if not chapter_path.exists():
            print(f"Chapter {chapter_num} not found, skipping")
            continue

        chapter_text = chapter_path.read_text()
        print(f"Chapter text: {len(chapter_text)} chars")

        # Build proper context package
        try:
            context = build_context_package(chapter_num)
            print(f"Context keys: {list(context.keys())}")
            print(f"  chapter_brief: {context.get('chapter_brief', {}).get('title', 'N/A')}")
            print(f"  voice: {len(context.get('voice', ''))} chars")
            print(f"  canon: {len(context.get('canon', ''))} chars")
            print(f"  characters: {len(context.get('characters', ''))} chars")
            print(f"  world: {len(context.get('world', ''))} chars")
        except Exception as e:
            print(f"Failed to build context: {e}")
            # Try simple context as fallback
            context = {
                "chapter_brief": {"title": f"Chapter {chapter_num}"},
                "voice": (NOVEL_DIR / "voice.md").read_text() if (NOVEL_DIR / "voice.md").exists() else "",
                "canon": (NOVEL_DIR / "canon.md").read_text() if (NOVEL_DIR / "canon.md").exists() else "",
                "characters": (NOVEL_DIR / "characters.md").read_text() if (NOVEL_DIR / "characters.md").exists() else "",
                "world": (NOVEL_DIR / "world.md").read_text() if (NOVEL_DIR / "world.md").exists() else "",
            }

        # Run Opus review
        try:
            result = opus_review(chapter_text, context, chapter_num)
            print(f"\nReview completed:")
            print(f"  Rating: {result.get('rating', 'N/A')}")
            print(f"  Items: {len(result.get('items', []))}")
            print(f"  Major issues: {result.get('severity', {}).get('major', 0)}")
            print(f"  Stop: {result.get('stop', False)}")
        except Exception as e:
            print(f"Review failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_review_phase()