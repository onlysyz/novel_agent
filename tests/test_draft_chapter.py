"""Tests for draft_chapter.py — chapter drafting logic."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.drafting.draft_chapter import (
    extract_chapter_brief,
    extract_next_chapter_opener,
    count_words,
    build_chapter_prompt,
    MIN_CHAPTER_WORDS,
    MAX_CHAPTER_WORDS,
    TARGET_WORDS_PER_CHAPTER,
)


SAMPLE_OUTLINE = """
# Outline

## Chapter 1: The Gathering Storm
POV: Sarah
Location: The ruined cathedral
Beat: Setup
Emotional Arc: Determination in the face of loss
Try-Fail Cycle: Sarah attempts to rally survivors but fails

Scene Beats:
- Sarah discovers the broken amulet
- She remembers her mother's last words
- The first survivor appears at the door

Foreshadow Plants:
- The amulet glows faintly when touched
- Mention of the old king's seal

Payoffs:
- None required this chapter

## Chapter 2: The Road West
POV: Marcus
Location: The mountain pass
Beat: Fun and Games
Emotional Arc: Reluctant commitment
Try-Fail Cycle: Marcus tries to avoid the quest but is forced into it

Scene Beats:
- Marcus meets the stranger at the tavern
- He receives the map fragment
- The mountain path reveals dangers ahead

Foreshadow Plants:
- The stranger bears an unfamiliar crest
- Horses show signs of exhaustion

Payoffs:
- None required this chapter
"""


class TestExtractChapterBrief:
    """Tests for extract_chapter_brief."""

    def test_extracts_title(self):
        """Chapter title extracted."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 1)
        assert brief["title"] == "The Gathering Storm"

    def test_extracts_pov(self):
        """POV character extracted."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 1)
        assert brief["pov"] == "Sarah"

    def test_extracts_beat(self):
        """Beat type extracted."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 2)
        assert brief["beat"] == "Fun and Games"

    def test_extracts_emotional_arc(self):
        """Emotional arc extracted."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 2)
        assert brief["emotional_arc"] == "Reluctant commitment"

    def test_extracts_scene_beats(self):
        """Scene beats collected into list."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 1)
        assert len(brief["scene_beats"]) == 3
        assert "Sarah discovers the broken amulet" in brief["scene_beats"]

    def test_extracts_foreshadow_plants(self):
        """Foreshadow plants collected."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 1)
        assert len(brief["foreshadow_plants"]) == 2
        assert "The amulet glows faintly when touched" in brief["foreshadow_plants"]

    def test_extracts_payoffs(self):
        """Payoff items collected."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 1)
        assert len(brief["payoff_payoffs"]) == 1
        assert "None required" in brief["payoff_payoffs"][0]

    def test_chapter_not_found(self):
        """Non-existent chapter returns defaults."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 99)
        assert brief["title"] == "Chapter 99"
        assert brief["scene_beats"] == []

    def test_word_target_default(self):
        """Word target defaults to TARGET_WORDS_PER_CHAPTER."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 1)
        assert brief["word_target"] == TARGET_WORDS_PER_CHAPTER

    def test_chapter_2_pov(self):
        """Chapter 2 POV extracted correctly."""
        brief = extract_chapter_brief(SAMPLE_OUTLINE, 2)
        assert brief["pov"] == "Marcus"


class TestExtractNextChapterOpener:
    """Tests for extract_next_chapter_opener."""

    def test_returns_next_chapter_hint(self):
        """Returns hint from next chapter's first scene beat."""
        hint = extract_next_chapter_opener(SAMPLE_OUTLINE, 1)
        assert "Marcus meets the stranger" in hint

    def test_returns_empty_for_last_chapter(self):
        """Last chapter returns empty string."""
        hint = extract_next_chapter_opener(SAMPLE_OUTLINE, 2)
        assert hint == ""


class TestCountWords:
    """Tests for count_words utility."""

    def test_counts_simple_words(self):
        """Simple word count."""
        assert count_words("Hello world") == 2

    def test_counts_empty_string(self):
        """Empty string returns 0."""
        assert count_words("") == 0

    def test_counts_with_punctuation(self):
        """Punctuation doesn't affect count."""
        assert count_words("Hello, world!") == 2


class TestBuildChapterPrompt:
    """Tests for build_chapter_prompt."""

    def test_returns_tuple(self):
        """Returns (system_prompt, user_prompt) tuple."""
        ctx = {
            "voice": "Literary and precise.",
            "world": "A realm of magic.",
            "characters": "Sarah: determined survivor.",
            "outline": SAMPLE_OUTLINE,
            "canon": "The old king ruled for 50 years.",
            "anti_patterns": "No fake emotion.",
            "chapter_brief": extract_chapter_brief(SAMPLE_OUTLINE, 1),
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_chapter_number(self):
        """System prompt references the chapter number."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": SAMPLE_OUTLINE,
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": extract_chapter_brief(SAMPLE_OUTLINE, 1),
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 5)
        assert "Chapter 5" in system

    def test_user_contains_brief_details(self):
        """User prompt includes chapter brief details."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": SAMPLE_OUTLINE,
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": extract_chapter_brief(SAMPLE_OUTLINE, 1),
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "The Gathering Storm" in user
        assert "Sarah" in user

    def test_user_contains_scene_beats(self):
        """User prompt lists scene beats."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": SAMPLE_OUTLINE,
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": extract_chapter_brief(SAMPLE_OUTLINE, 1),
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Sarah discovers the broken amulet" in user

    def test_includes_prev_ending_when_present(self):
        """Previous chapter ending included in user prompt."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": SAMPLE_OUTLINE,
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": extract_chapter_brief(SAMPLE_OUTLINE, 1),
            "next_chapter_hint": "",
            "prev_ending": "The door creaked open...",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "PREVIOUS CHAPTER ENDING" in user
        assert "The door creaked open" in user

    def test_excludes_prev_ending_when_empty(self):
        """PREVIOUS CHAPTER ENDING section omitted when empty."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": SAMPLE_OUTLINE,
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": extract_chapter_brief(SAMPLE_OUTLINE, 1),
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "PREVIOUS CHAPTER ENDING" not in user
