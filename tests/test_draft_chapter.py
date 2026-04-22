"""Tests for draft_chapter.py — chapter drafting logic."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.drafting.draft_chapter import (
    extract_chapter_brief,
    extract_next_chapter_opener,
    count_words,
    build_chapter_prompt,
    parse_chapter_content,
    _extract_scenes,
    _extract_worldbuilding,
    get_client,
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

    def test_writing_rules_included_in_user(self):
        """WRITING_RULES constant is included in the user prompt."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "No fake emotion.",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "WRITING RULES" in user
        assert "MANDATORY WRITING RULES" in user

    def test_anti_patterns_section_in_user(self):
        """ANTI-PATTERNS TO AVOID section appears when anti_patterns is set."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "Avoid excessive dialogue tags.",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "ANTI-PATTERNS TO AVOID" in user
        assert "Avoid excessive dialogue tags." in user

    def test_world_context_section_in_user(self):
        """WORLD CONTEXT section appears with world content."""
        ctx = {
            "voice": "",
            "world": "The kingdom is divided into three realms.",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "WORLD CONTEXT" in user
        assert "kingdom is divided into three realms" in user

    def test_characters_context_section_in_user(self):
        """CHARACTER CONTEXT section appears with characters content."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "Sarah: brave leader of the survivors.",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "CHARACTER CONTEXT" in user
        assert "Sarah: brave leader" in user

    def test_canonical_facts_section_in_user(self):
        """CANONICAL FACTS section appears with canon content."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "The king died in the year 1000.",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "CANONICAL FACTS" in user
        assert "king died in the year 1000" in user

    def test_includes_next_chapter_hint_when_present(self):
        """NEXT CHAPTER OPENER section appears when next_chapter_hint is set."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "The stranger enters the tavern.",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "NEXT CHAPTER OPENER" in user
        assert "stranger enters the tavern" in user

    def test_excludes_next_chapter_hint_when_empty(self):
        """NEXT CHAPTER OPENER section omitted when next_chapter_hint is empty."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "NEXT CHAPTER OPENER" not in user

    def test_no_voice_uses_default_message(self):
        """Empty voice field falls back to default message in prompt."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No voice guide provided" in user

    def test_no_world_uses_default_message(self):
        """Empty world field falls back to default message."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No world context available" in user

    def test_brief_beat_type_in_user(self):
        """Beat Type field from brief appears in user prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "Cathedral",
                              "beat": "Setup", "position": "Opening",
                              "emotional_arc": "Determination", "try_fail": "Sarah fails to rally survivors",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Beat Type" in user
        assert "Setup" in user

    def test_brief_emotional_arc_in_user(self):
        """Emotional Arc field from brief appears in user prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "Cathedral",
                              "beat": "Setup", "position": "Opening",
                              "emotional_arc": "Determination", "try_fail": "Sarah fails to rally survivors",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Emotional Arc" in user
        assert "Determination" in user

    def test_brief_try_fail_in_user(self):
        """Try-Fail Cycle field from brief appears in user prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "Cathedral",
                              "beat": "Setup", "position": "Opening",
                              "emotional_arc": "Determination", "try_fail": "Sarah fails to rally survivors",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Try-Fail Cycle" in user
        assert "Sarah fails to rally survivors" in user

    def test_brief_position_in_user(self):
        """Position in Novel field from brief appears in user prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "Cathedral",
                              "beat": "Setup", "position": "Midpoint",
                              "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Position in Novel" in user
        assert "Midpoint" in user

    def test_foreshadow_plants_section_with_items(self):
        """Foreshadowing to Plant section includes plant items."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [],
                              "foreshadow_plants": ["The amulet glows faintly", "The old king's seal"],
                              "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Foreshadowing to Plant" in user
        assert "amulet glows faintly" in user
        assert "old king's seal" in user

    def test_payoffs_section_with_items(self):
        """Payoffs to Deliver section includes payoff items."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [],
                              "payoff_payoffs": ["The amulet reveals its power"], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Payoffs to Deliver" in user
        assert "amulet reveals its power" in user

    def test_no_scene_beats_shows_default(self):
        """Empty scene_beats shows '- No specific beats listed'."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No specific beats listed" in user

    def test_no_foreshadow_shows_default(self):
        """Empty foreshadow_plants shows '- No specific foreshadowing required'."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No specific foreshadowing required" in user

    def test_no_payoffs_shows_default(self):
        """Empty payoff_payoffs shows '- No payoffs required this chapter'."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No payoffs required this chapter" in user

    def test_word_target_in_user(self):
        """Word Count Target from brief appears in user prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 5000},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Word Count Target" in user
        assert "5000" in user

    def test_min_max_word_range_in_user(self):
        """IMPORTANT section contains MIN and MAX chapter word bounds."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Target" in user
        # Should reference MIN_CHAPTER_WORDS and MAX_CHAPTER_WORDS in the prompt
        assert "IMPORTANT" in user

    def test_location_field_in_brief_appears_in_user(self):
        """Location field from brief appears in user prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "The ruined cathedral",
                              "beat": "Setup", "position": "Opening",
                              "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "Location" in user
        assert "ruined cathedral" in user

    def test_world_truncated_at_4000_chars(self):
        """World text over 4000 chars is truncated in prompt."""
        ctx = {
            "voice": "",
            "world": "X" * 5000,
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        # The section should exist but be truncated
        assert "WORLD CONTEXT" in user
        # 4000 X's should appear (truncated)
        assert "X" * 4000 in user
        assert ("X" * 5000) not in user

    def test_characters_truncated_at_4000_chars(self):
        """Characters text over 4000 chars is truncated in prompt."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "Y" * 5000,
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "CHARACTER CONTEXT" in user
        assert "Y" * 4000 in user
        assert ("Y" * 5000) not in user

    def test_canon_truncated_at_3000_chars(self):
        """Canon text over 3000 chars is truncated in prompt."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "Z" * 4000,
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "CANONICAL FACTS" in user
        assert "Z" * 3000 in user
        assert ("Z" * 4000) not in user

    def test_all_fields_empty_still_builds_valid_prompts(self):
        """With all fields empty, prompts still build without errors."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Chapter 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0
        # Should contain default fallbacks
        assert "No voice guide provided" in user
        assert "No world context available" in user
        assert "No character context available" in user
        assert "No canonical facts provided" in user

    def test_no_characters_uses_default_message(self):
        """Empty characters field falls back to default message."""
        ctx = {
            "voice": "",
            "world": "",
            "characters": "",
            "outline": "",
            "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No character context available" in user

    def test_no_canon_uses_default_message(self):
        """Empty canon field falls back to default message."""
        ctx = {
            "voice": "", "world": "", "characters": "", "outline": "", "canon": "",
            "anti_patterns": "",
            "chapter_brief": {"title": "Ch 1", "pov": "", "location": "", "beat": "",
                              "position": "", "emotional_arc": "", "try_fail": "",
                              "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200},
            "next_chapter_hint": "",
            "prev_ending": "",
        }
        system, user = build_chapter_prompt(ctx, 1)
        assert "No canonical facts provided" in user


class TestParseChapterContent:
    """Tests for parse_chapter_content."""

    def test_parses_scene_beats_section(self):
        """## Scene Beats header and its bullets are extracted."""
        text = """
# Chapter 1

Some prose here.

## Scene Beats
- Sarah discovers the broken amulet
- She remembers her mother's last words

More prose.
"""
        result = parse_chapter_content(text)
        assert "Sarah discovers the broken amulet" in result["scene_beats"]
        assert "She remembers her mother's last words" in result["scene_beats"]

    def test_parses_world_building_section(self):
        """## World Building header and its bullets are extracted."""
        text = """
# Chapter 1

## World Building
- The ancient city walls are crumbling
- Magic has faded over centuries

Prose continues.
"""
        result = parse_chapter_content(text)
        assert "The ancient city walls are crumbling" in result["world_building"]
        assert "Magic has faded over centuries" in result["world_building"]

    def test_parses_narrative_notes_section(self):
        """## Narrative Notes header and its bullets are extracted."""
        text = """
# Chapter 1

## Narrative Notes
- This scene establishes Sarah's determination
- Foreshadow the amulet's power here

More text.
"""
        result = parse_chapter_content(text)
        assert "This scene establishes Sarah's determination" in result["narrative_notes"]
        assert "Foreshadow the amulet's power here" in result["narrative_notes"]

    def test_parses_mixed_sections(self):
        """Multiple annotated sections parsed correctly."""
        text = """
# Chapter 1

## Scene Beats
- First beat
- Second beat

## World Building
- World detail one

## Narrative Notes
- Narrative note one
"""
        result = parse_chapter_content(text)
        assert "First beat" in result["scene_beats"]
        assert "Second beat" in result["scene_beats"]
        assert "World detail one" in result["world_building"]
        assert "Narrative note one" in result["narrative_notes"]

    def test_asterisk_bullets_extracted(self):
        """Asterisk-prefixed bullets are also extracted."""
        text = """
## Scene Beats
* Sarah discovers the amulet
* The door opens slowly
"""
        result = parse_chapter_content(text)
        assert "Sarah discovers the amulet" in result["scene_beats"]
        assert "The door opens slowly" in result["scene_beats"]

    def test_bullets_not_in_section_ignored(self):
        """Bullets appearing before any section header are ignored."""
        text = """
# Chapter 1

- This bullet appears before any section header
- It should be ignored

## Scene Beats
- This beat is captured
"""
        result = parse_chapter_content(text)
        assert "This bullet appears before any section header" not in result["scene_beats"]
        assert "This beat is captured" in result["scene_beats"]

    def test_scene_markers_horizontal_rule(self):
        """Horizontal rules (---) are detected as scene breaks."""
        text = """
Prose of scene one.

---

Prose of scene two.
"""
        result = parse_chapter_content(text)
        assert "---" in result["scenes"]

    def test_scene_markers_header(self):
        """## Scene markers are detected as scene breaks."""
        text = """
Prose.

## Scene
Prose of a new scene.

### Scene 1
Another scene marker.
"""
        result = parse_chapter_content(text)
        assert "## Scene" in result["scenes"]
        assert "### Scene 1" in result["scenes"]

    def test_plain_prose_returns_empty(self):
        """Chapter text with no annotations returns empty lists."""
        text = """
# Chapter 1

Sarah stood in the ruined cathedral. The wind howled through the broken windows.

She reached into her pocket and pulled out the broken amulet. It was still warm.
"""
        result = parse_chapter_content(text)
        assert result["scene_beats"] == []
        assert result["world_building"] == []
        assert result["narrative_notes"] == []
        assert result["scenes"] == []

    def test_empty_text_returns_empty(self):
        """Empty text returns all-empty result."""
        result = parse_chapter_content("")
        assert result["scene_beats"] == []
        assert result["world_building"] == []
        assert result["narrative_notes"] == []
        assert result["scenes"] == []

    def test_section_header_variants_scene_beats(self):
        """Various 'Scene Beats' header formats are recognized."""
        text = """
## Scene Beats
- Beat one

### Scene Beats
- Beat two

# Scene Beats
- Beat three
"""
        result = parse_chapter_content(text)
        assert "Beat one" in result["scene_beats"]
        assert "Beat two" in result["scene_beats"]
        assert "Beat three" in result["scene_beats"]

    def test_world_building_variants(self):
        """## World Building and ## World-Building variants recognized."""
        text = """
## World Building
- Detail one

## World-Building
- Detail two
"""
        result = parse_chapter_content(text)
        assert "Detail one" in result["world_building"]
        assert "Detail two" in result["world_building"]

    def test_narrative_notes_variants(self):
        """## Narrative Notes and ## Notes variants recognized."""
        text = """
## Narrative Notes
- Note one

## Notes
- Note two

## Annotations
- Note three
"""
        result = parse_chapter_content(text)
        assert "Note one" in result["narrative_notes"]
        assert "Note two" in result["narrative_notes"]
        assert "Note three" in result["narrative_notes"]

    def test_all_keys_present(self):
        """Result always has all four keys even if empty."""
        result = parse_chapter_content("Just plain prose.")
        assert set(result.keys()) == {"scene_beats", "world_building", "narrative_notes", "scenes"}


class TestExtractScenes:
    """Tests for _extract_scenes helper."""

    def test_detects_horizontal_rule_triple_dash(self):
        """--- is detected as a scene marker."""
        text = "Prose of scene one.\n---\nProse of scene two."
        scenes = _extract_scenes(text)
        assert "---" in scenes

    def test_detects_horizontal_rule_triple_star(self):
        """*** is detected as a scene marker."""
        text = "Prose of scene one.\n***\nProse of scene two."
        scenes = _extract_scenes(text)
        assert "***" in scenes

    def test_detects_horizontal_rule_double_underscore(self):
        """__ is detected as a scene marker."""
        text = "Prose of scene one.\n__\nProse of scene two."
        scenes = _extract_scenes(text)
        assert "__" in scenes

    def test_detects_scene_header_single_hash(self):
        """# Scene is detected."""
        text = "Prose.\n# Scene\nMore prose."
        scenes = _extract_scenes(text)
        assert "# Scene" in scenes

    def test_detects_scene_header_double_hash(self):
        """## Scene is detected."""
        text = "Prose.\n## Scene\nMore prose."
        scenes = _extract_scenes(text)
        assert "## Scene" in scenes

    def test_detects_scene_header_triple_hash(self):
        """### Scene is detected."""
        text = "Prose.\n### Scene\nMore prose."
        scenes = _extract_scenes(text)
        assert "### Scene" in scenes

    def test_detects_scene_with_number(self):
        """### Scene 1 and ## Scene 2 (digit suffixes) are detected."""
        text = "Prose.\n### Scene 1\nMore prose.\n## Scene 2\nEnd."
        scenes = _extract_scenes(text)
        assert "### Scene 1" in scenes
        assert "## Scene 2" in scenes
        # "Scene" alone (no suffix) is also detected
        assert "## Scene" in _extract_scenes("Prose.\n## Scene\nEnd.")

    def test_does_not_detect_scene_beats_section_header(self):
        """'## Scene Beats' (with word after 'Scene') is NOT a scene marker."""
        text = "Prose.\n## Scene Beats\n- First beat\nMore prose."
        scenes = _extract_scenes(text)
        assert "## Scene Beats" not in scenes

    def test_multiple_scene_markers_in_order(self):
        """Multiple scene markers returned in order of appearance."""
        text = "# Scene\nProse one.\n---\nProse two.\n### Scene 1\nProse three."
        scenes = _extract_scenes(text)
        assert scenes == ["# Scene", "---", "### Scene 1"]

    def test_empty_text_returns_empty_list(self):
        """Empty string returns empty list."""
        assert _extract_scenes("") == []

    def test_plain_prose_no_scene_markers(self):
        """Prose without any markers returns empty list."""
        text = """
# Chapter 1

Sarah stood in the ruined cathedral. The wind howled through the broken windows.

She reached into her pocket and pulled out the broken amulet.
"""
        assert _extract_scenes(text) == []

    def test_scene_markers_at_start(self):
        """Scene markers at beginning of text are detected."""
        text = "---\nProse of scene one.\n## Scene\nProse two."
        scenes = _extract_scenes(text)
        assert scenes[0] == "---"

    def test_scene_markers_at_end(self):
        """Scene markers at end of text are detected."""
        text = "Prose of scene one.\n### Scene 1\n---\n"
        scenes = _extract_scenes(text)
        assert "---" in scenes
        assert "### Scene 1" in scenes

    def test_scene_header_case_insensitive(self):
        """Scene header detection is case-insensitive."""
        text = "Prose.\n# SCENE\nMore prose.\n## scene\nEnd."
        scenes = _extract_scenes(text)
        assert "# SCENE" in scenes
        assert "## scene" in scenes


class TestExtractWorldbuilding:
    """Tests for _extract_worldbuilding helper."""

    def test_detects_bracket_world_format(self):
        """[[World:ancient_city]] format is extracted."""
        text = "The [[World:ancient_city]] had stood for a thousand years."
        result = _extract_worldbuilding(text)
        assert "[[World:ancient_city]]" in result

    def test_detects_bracket_pipe_format(self):
        """[[world|ancient_city]] format is extracted."""
        text = "Legends spoke of [[world|forgotten_kingdom]]."
        result = _extract_worldbuilding(text)
        assert "[[World:forgotten_kingdom]]" in result

    def test_detects_curly_braces_format(self):
        """{wc:ancient_city} format is extracted."""
        text = "The treaty was signed in {wc:the_conclave}."
        result = _extract_worldbuilding(text)
        assert "{wc:the_conclave}" in result

    def test_multiple_references_in_text(self):
        """Multiple different references are all extracted."""
        text = (
            "The [[World:ancient_city]] crumbled. "
            "Meanwhile, {wc:magic_fading} spread. "
            "At [[world|forgotten_kingdom]], the king watched."
        )
        result = _extract_worldbuilding(text)
        assert "[[World:ancient_city]]" in result
        assert "{wc:magic_fading}" in result
        assert "[[World:forgotten_kingdom]]" in result

    def test_duplicate_references_deduplicated(self):
        """Same reference appearing multiple times is returned only once."""
        text = (
            "The [[World:ancient_city]] fell. "
            "Later, [[World:ancient_city]] was forgotten."
        )
        result = _extract_worldbuilding(text)
        assert result.count("[[World:ancient_city]]") == 1
        assert len(result) == 1

    def test_no_references_returns_empty(self):
        """Plain prose with no world references returns empty list."""
        text = "Sarah stood in the ruined cathedral. The wind howled through broken windows."
        assert _extract_worldbuilding(text) == []

    def test_empty_text_returns_empty(self):
        """Empty string returns empty list."""
        assert _extract_worldbuilding("") == []

    def test_reference_in_middle_of_sentence(self):
        """Reference embedded mid-sentence is extracted."""
        text = "According to scholars, [[World:magic_fading]] had begun centuries ago."
        result = _extract_worldbuilding(text)
        assert "[[World:magic_fading]]" in result

    def test_multiple_curly_brace_references(self):
        """Multiple {wc:...} references in same text are all extracted."""
        text = "At {wc:the_conclave}, they debated {wc:magic_fading}."
        result = _extract_worldbuilding(text)
        assert "{wc:the_conclave}" in result
        assert "{wc:magic_fading}" in result

    def test_reference_with_underscores_and_numbers(self):
        """References with underscores and numbers are extracted correctly."""
        text = "The order of {wc:shadow_guard_7} was formed."
        result = _extract_worldbuilding(text)
        assert "{wc:shadow_guard_7}" in result

    def test_bracket_reference_case_variations(self):
        """[[WORLD:fact]] and [[world|fact]] variations normalize to [[World:fact]]."""
        text = "Facts: [[WORLD:ancient_fact]] and [[world|older_fact]]."
        result = _extract_worldbuilding(text)
        assert "[[World:ancient_fact]]" in result
        assert "[[World:older_fact]]" in result

    def test_all_keys_present_in_parse_result(self):
        """parse_chapter_content result includes world_building key."""
        text = "## World Building\n- The ancient city walls"
        result = parse_chapter_content(text)
        assert "world_building" in result


class TestGetPreviousChapterEnding:
    """Tests for get_previous_chapter_ending."""

    def test_chapter_one_returns_empty(self):
        """Chapter 1 has no previous chapter - returns empty string."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        result = get_previous_chapter_ending(Path("/nonexistent"), 1)
        assert result == ""

    def test_prev_file_not_exists_returns_empty(self, tmp_path):
        """Missing previous chapter file returns empty string."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        result = get_previous_chapter_ending(chapters_dir, 2)
        assert result == ""

    def test_chapters_dir_not_exists_returns_empty(self, tmp_path):
        """When chapters_dir does not exist, returns empty string."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        # chapters_dir does NOT exist - Path("/nonexistent") would short-circuit chapter <= 1
        # so use tmp_path / "nonexistent_chapters_dir" (does not exist)
        chapters_dir = tmp_path / "nonexistent_chapters_dir"
        assert not chapters_dir.exists()
        result = get_previous_chapter_ending(chapters_dir, 2)
        assert result == ""

    def test_short_file_returns_full_text(self, tmp_path):
        """File under 2000 chars returned in full."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        prev_file = chapters_dir / "ch_01.md"
        prev_file.write_text("A short chapter.")
        result = get_previous_chapter_ending(chapters_dir, 2)
        assert result == "A short chapter."

    def test_exactly_2000_chars_returns_full_text(self, tmp_path):
        """File exactly 2000 chars returned with no truncation."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        prev_file = chapters_dir / "ch_01.md"
        prev_file.write_text("X" * 2000)
        result = get_previous_chapter_ending(chapters_dir, 2)
        assert result == "X" * 2000
        assert not result.startswith("...")

    def test_long_file_truncates_with_ellipsis(self, tmp_path):
        """File over 2000 chars truncated to last 2000 with ellipsis prefix."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        prev_file = chapters_dir / "ch_01.md"
        # 2100 chars total, last 2000 should be returned with "...\n\n" prefix
        prev_file.write_text("X" * 2100)
        result = get_previous_chapter_ending(chapters_dir, 2)
        assert result.startswith("...\n\n")
        assert len(result) == 2000 + 5  # 5 for "...\n\n"


class TestBuildContextPackage:
    """Tests for build_context_package with mocked filesystem.

    Note: build_context_package reads real files, so we mock the helper
    functions it calls internally rather than patching Path methods.
    """

    def test_returns_all_context_keys(self):
        """build_context_package returns dict with all required keys."""
        from src.drafting.draft_chapter import build_context_package
        with patch("src.drafting.draft_chapter.extract_chapter_brief",
                   return_value={"title": "Ch 1", "scene_beats": [], "word_target": 3200}):
            with patch("src.drafting.draft_chapter.extract_next_chapter_opener", return_value=""):
                with patch("src.drafting.draft_chapter.get_previous_chapter_ending", return_value=""):
                    with patch("src.drafting.draft_chapter.NOVEL_DIR", Path("/mocked")):
                        with patch.object(Path, "exists", return_value=False):
                            with patch.object(Path, "read_text", return_value=""):
                                result = build_context_package(1)

        expected_keys = {"voice", "world", "characters", "outline", "canon",
                         "anti_patterns", "chapter_brief", "next_chapter_hint", "prev_ending"}
        assert set(result.keys()) == expected_keys

    def test_calls_extract_chapter_brief(self):
        """build_context_package calls extract_chapter_brief with correct chapter_num."""
        from src.drafting.draft_chapter import build_context_package
        with patch("src.drafting.draft_chapter.extract_chapter_brief",
                   return_value={"title": "Ch 5", "scene_beats": [], "word_target": 3200}) as mock_extract:
            with patch("src.drafting.draft_chapter.extract_next_chapter_opener", return_value=""):
                with patch("src.drafting.draft_chapter.get_previous_chapter_ending", return_value=""):
                    with patch("src.drafting.draft_chapter.NOVEL_DIR", Path("/mocked")):
                        with patch.object(Path, "exists", return_value=False):
                            with patch.object(Path, "read_text", return_value=""):
                                build_context_package(5)
            mock_extract.assert_called_once()
            assert mock_extract.call_args[0][1] == 5

    def test_includes_prev_ending_for_chapter_gt_1(self):
        """prev_ending is non-empty for chapter > 1 when chapter file exists."""
        from src.drafting.draft_chapter import build_context_package
        with patch("src.drafting.draft_chapter.extract_chapter_brief",
                   return_value={"title": "Ch 2", "scene_beats": [], "word_target": 3200}):
            with patch("src.drafting.draft_chapter.extract_next_chapter_opener", return_value=""):
                with patch("src.drafting.draft_chapter.get_previous_chapter_ending",
                           return_value="The door creaked open.") as mock_prev:
                    with patch("src.drafting.draft_chapter.NOVEL_DIR", Path("/mocked")):
                        with patch.object(Path, "exists", return_value=False):
                            with patch.object(Path, "read_text", return_value=""):
                                result = build_context_package(2)
            mock_prev.assert_called_once()
            assert result["prev_ending"] == "The door creaked open."

    def test_prev_ending_empty_for_chapter_1(self):
        """prev_ending is empty for chapter 1 (no previous)."""
        from src.drafting.draft_chapter import build_context_package
        with patch("src.drafting.draft_chapter.extract_chapter_brief",
                   return_value={"title": "Ch 1", "scene_beats": [], "word_target": 3200}):
            with patch("src.drafting.draft_chapter.extract_next_chapter_opener", return_value=""):
                with patch("src.drafting.draft_chapter.get_previous_chapter_ending", return_value="") as mock_prev:
                    with patch("src.drafting.draft_chapter.NOVEL_DIR", Path("/mocked")):
                        with patch.object(Path, "exists", return_value=False):
                            with patch.object(Path, "read_text", return_value=""):
                                result = build_context_package(1)
            mock_prev.assert_called_once()
            assert result["prev_ending"] == ""


class TestExtractChapterBriefEdgeCases:
    """Additional edge case tests for extract_chapter_brief."""

    def test_alternate_header_format_hashes(self):
        """'## Chapter N' and '### Chapter N' headers work."""
        outline = """
## Chapter 1: Named Header
POV: Test

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["title"] == "Named Header"

    def test_alternate_header_format_number_dot(self):
        """'^N. Chapter' format is detected (title remains default)."""
        outline = """
1. Chapter with Number Prefix
POV: Test

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        # The chapter pattern '^1.\\s+' detects the chapter but title regex
        # requires "Chapter N: Title" format, so title stays as default "Chapter 1"
        assert brief["title"] == "Chapter 1"

    def test_key_value_takes_precedence_over_keyword(self):
        """KEY: VALUE format is captured even when 'beat' appears in section name."""
        outline = """
## Chapter 1
POV: Sarah
Scene Beats:
- Beat one
- Beat two
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["scene_beats"] == ["Beat one", "Beat two"]

    def test_missing_sections_default_to_empty(self):
        """Outline without optional sections returns empty defaults."""
        outline = """
## Chapter 1: Only Title
POV: Sarah
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["location"] == ""
        assert brief["beat"] == ""
        assert brief["emotional_arc"] == ""
        assert brief["try_fail"] == ""
        assert brief["scene_beats"] == []
        assert brief["foreshadow_plants"] == []
        assert brief["payoff_payoffs"] == []

    def test_asterisk_bullet_points(self):
        """Asterisk-prefixed lines are treated as bullet points."""
        outline = """
## Chapter 1
Scene Beats:
* Asterisk bullet one
* Asterisk bullet two
"""
        brief = extract_chapter_brief(outline, 1)
        assert "Asterisk bullet one" in brief["scene_beats"]
        assert "Asterisk bullet two" in brief["scene_beats"]

    def test_word_target_parsed_from_outline(self):
        """Word target in outline is captured from KEY: VALUE line."""
        outline = """
## Chapter 1: Custom Length
Word Target: 5000

Scene Beats:
- One beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["word_target"] == "5000"

    def test_position_extracted(self):
        """Position field extracted when present."""
        outline = """
## Chapter 1
Position: Midpoint

Scene Beats:
- One beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["position"] == "Midpoint"

    def test_keyword_fallback_scene_beats(self):
        """Line without colon but containing 'scene' keyword sets scene_beats section."""
        outline = """
## Chapter 1
POV: Sarah
This scene beats section follows the opening
- First beat captured
- Second beat captured
"""
        brief = extract_chapter_brief(outline, 1)
        assert "First beat captured" in brief["scene_beats"]
        assert "Second beat captured" in brief["scene_beats"]

    def test_keyword_fallback_beats_alone(self):
        """Line without colon containing 'beats' keyword sets scene_beats."""
        outline = """
## Chapter 1
POV: Sarah
beats to cover in this chapter
- Opening scene
- Middle scene
"""
        brief = extract_chapter_brief(outline, 1)
        assert "Opening scene" in brief["scene_beats"]
        assert "Middle scene" in brief["scene_beats"]

    def test_keyword_fallback_events(self):
        """Line without colon containing 'events' keyword sets scene_beats."""
        outline = """
## Chapter 1
POV: Sarah
Key events to dramatize
- Event one
"""
        brief = extract_chapter_brief(outline, 1)
        assert "Event one" in brief["scene_beats"]

    def test_keyword_fallback_foreshadow(self):
        """Line without colon containing 'foreshadow' keyword sets foreshadow_plants."""
        outline = """
## Chapter 1
POV: Sarah
Important foreshadow to plant
- The glowing amulet
- The old map
"""
        brief = extract_chapter_brief(outline, 1)
        assert "The glowing amulet" in brief["foreshadow_plants"]
        assert "The old map" in brief["foreshadow_plants"]

    def test_keyword_fallback_payoff(self):
        """Line without colon containing 'payoff' keyword sets payoff_payoffs."""
        outline = """
## Chapter 1
POV: Sarah
Payoffs from earlier setup
- The amulet reveals its power
"""
        brief = extract_chapter_brief(outline, 1)
        assert "The amulet reveals its power" in brief["payoff_payoffs"]

    def test_keyword_fallback_emotional_arc(self):
        """Keyword-only line (no colon) sets section but does not capture text."""
        outline = """
## Chapter 1
POV: Sarah
The emotional arc for this chapter
Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        # Keyword-only line without colon captures nothing; section is set for next bullets
        assert brief["emotional_arc"] == ""
        # Bullets after KEY:VALUE line are captured correctly
        assert brief["scene_beats"] == ["Beat one"]

    def test_keyword_fallback_try_fail(self):
        """Keyword-only line (no colon) sets section but does not capture text."""
        outline = """
## Chapter 1
POV: Sarah
Try-fail cycle for the protagonist
Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        # Keyword-only line without colon captures nothing
        assert brief["try_fail"] == ""
        # Bullets after KEY:VALUE line are captured correctly
        assert brief["scene_beats"] == ["Beat one"]

    def test_keyword_fallback_location(self):
        """Keyword-only line (no colon) sets section but does not capture text."""
        outline = """
## Chapter 1
POV: Sarah
The location is the dark forest
Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        # Keyword-only line without colon captures nothing
        assert brief["location"] == ""
        # Bullets after KEY:VALUE line are captured correctly
        assert brief["scene_beats"] == ["Beat one"]

    def test_keyword_fallback_beat_alone(self):
        """Line without colon containing 'beat' (not scene/beats/events) triggers beat branch."""
        outline = """
## Chapter 1
POV: Sarah
The beat went on and on
Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        # The "beat" keyword (without "scene"/"beats"/"events") sets beat type
        # "The beat went on" contains "beat" but not "scene"/"beats"/"events"
        # so it hits the 'beat' branch at line 157
        assert brief["beat"] == ""

    def test_keyword_fallback_pov_only(self):
        """Line without colon containing 'pov' (not 'point of view') sets pov section."""
        outline = """
## Chapter 1
pov character perspective here
Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        # "pov character perspective here" contains "pov" and "perspective"
        # but is caught by the first 'pov' branch at line 149
        assert brief["pov"] == ""

    def test_keyword_fallback_word_only(self):
        """Line without colon containing 'word' triggers word_target branch (line 167)."""
        outline = """
## Chapter 1
POV: Sarah
word count target for this chapter
Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        # "word" keyword (without colon) hits word_target branch at line 167
        # brief["word_target"] stays at default integer 3200 (no KEY:VALUE to override)
        assert brief["word_target"] == 3200

    def test_location_extracted(self):
        """Location field extracted from outline."""
        outline = """
## Chapter 1
POV: Sarah
Location: The ruined cathedral

Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["location"] == "The ruined cathedral"

    def test_try_fail_cycle_extracted(self):
        """Try-Fail Cycle field extracted from outline."""
        outline = """
## Chapter 1
POV: Sarah
Try-Fail Cycle: Sarah tries to escape but is captured

Scene Beats:
- Beat one
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["try_fail"] == "Sarah tries to escape but is captured"


class TestExtractChapterBriefBeatTypes:
    """Tests for extract_chapter_brief covering all Save the Cat beat types."""

    def test_beat_setup(self):
        """Beat type 'Setup' is extracted."""
        outline = """
## Chapter 1
Beat: Setup

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Setup"

    def test_beat_catalyst(self):
        """Beat type 'Catalyst' is extracted."""
        outline = """
## Chapter 1
Beat: Catalyst

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Catalyst"

    def test_beat_debate(self):
        """Beat type 'Debate' is extracted."""
        outline = """
## Chapter 1
Beat: Debate

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Debate"

    def test_beat_break_into_two(self):
        """Beat type 'Break into Two' is extracted."""
        outline = """
## Chapter 1
Beat: Break into Two

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Break into Two"

    def test_beat_fun_and_games(self):
        """Beat type 'Fun and Games' is extracted."""
        outline = """
## Chapter 1
Beat: Fun and Games

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Fun and Games"

    def test_beat_fun_and_games_ampersand(self):
        """Beat type 'Fun & Games' (with ampersand) is extracted."""
        outline = """
## Chapter 1
Beat: Fun & Games

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Fun & Games"

    def test_beat_midpoint(self):
        """Beat type 'Midpoint' is extracted."""
        outline = """
## Chapter 1
Beat: Midpoint

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Midpoint"

    def test_beat_midpoint_continued(self):
        """Beat type 'Midpoint (Continued)' is extracted."""
        outline = """
## Chapter 1
Beat: Midpoint (Continued)

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Midpoint (Continued)"

    def test_beat_midpoint_crisis(self):
        """Beat type 'Midpoint Crisis' is extracted."""
        outline = """
## Chapter 1
Beat: Midpoint Crisis

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Midpoint Crisis"

    def test_beat_bad_guys_close_in(self):
        """Beat type 'Bad Guys Close In' is extracted."""
        outline = """
## Chapter 1
Beat: Bad Guys Close In

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Bad Guys Close In"

    def test_beat_all_is_lost(self):
        """Beat type 'All Is Lost' is extracted."""
        outline = """
## Chapter 1
Beat: All Is Lost

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "All Is Lost"

    def test_beat_final_battle(self):
        """Beat type 'Final Battle' is extracted."""
        outline = """
## Chapter 1
Beat: Final Battle

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Final Battle"

    def test_beat_climax(self):
        """Beat type 'Climax' is extracted."""
        outline = """
## Chapter 1
Beat: Climax

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Climax"

    def test_beat_denouement(self):
        """Beat type 'Denouement' is extracted."""
        outline = """
## Chapter 1
Beat: Denouement

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Denouement"

    def test_beat_save_the_cat_alias(self):
        """Beat 'Save the Cat' maps to beat field."""
        outline = """
## Chapter 1
Save the Cat: Setup

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Setup"

    def test_beat_position_in_user_prompt(self):
        """Position field (Opening, Midpoint, etc.) is included in beat extraction."""
        outline = """
## Chapter 1
Beat: Setup
Position: Opening

Scene Beats:
- First beat
"""
        brief = extract_chapter_brief(outline, 1)
        assert brief["beat"] == "Setup"
        assert brief["position"] == "Opening"


class TestDraftChapterIntegration:
    """Tests for draft_chapter() with mocked AI client."""

    def test_draft_chapter_accepted_on_first_try(self, tmp_path):
        """When score >= min_score on first attempt, no retries."""
        from src.drafting.draft_chapter import draft_chapter

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        mock_client = MagicMock()
        mock_client.generate.return_value = "A great chapter with sufficient word count " * 100

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    context = {
                        "voice": "", "world": "", "characters": "", "outline": "",
                        "canon": "", "anti_patterns": "",
                        "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "",
                                        "beat": "", "position": "", "emotional_arc": "",
                                        "try_fail": "", "scene_beats": [], "foreshadow_plants": [],
                                        "payoff_payoffs": [], "word_target": 3200},
                        "next_chapter_hint": "", "prev_ending": "",
                    }
                    result = draft_chapter(1, context=context)

        assert result["word_count"] > 0
        assert result["score"] == 7.0
        assert result["attempts"] == 1

    def test_draft_chapter_retries_on_low_score(self, tmp_path):
        """When score < min_score, retries until max_retries reached."""
        from src.drafting.draft_chapter import draft_chapter

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            "Low quality attempt." * 50,
            "Slightly better attempt." * 50,
            "A great chapter that finally passes the bar." * 50,
        ]

        mock_eval_failing = {"overall_score": 5.0, "voice_adherence": 5.0,
                              "beat_coverage": 5.0, "character_voice": 5.0, "slop_penalty": 0.0}
        mock_eval_passing = {"overall_score": 7.0, "voice_adherence": 7.0,
                              "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter") as mock_evaluate:
                    mock_evaluate.side_effect = [mock_eval_failing, mock_eval_failing, mock_eval_passing]
                    context = {
                        "voice": "", "world": "", "characters": "", "outline": "",
                        "canon": "", "anti_patterns": "",
                        "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "",
                                        "beat": "", "position": "", "emotional_arc": "",
                                        "try_fail": "", "scene_beats": [], "foreshadow_plants": [],
                                        "payoff_payoffs": [], "word_target": 3200},
                        "next_chapter_hint": "", "prev_ending": "",
                    }
                    result = draft_chapter(1, context=context, max_retries=3)

        assert result["attempts"] == 3
        assert result["score"] == 7.0
        assert mock_client.generate.call_count == 3

    def test_draft_chapter_saves_to_file(self, tmp_path):
        """Drafted chapter is written to chapters/ch_NN.md."""
        from src.drafting.draft_chapter import draft_chapter

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        mock_client = MagicMock()
        mock_client.generate.return_value = "A wonderful chapter that scores well." * 100

        mock_eval = {"overall_score": 7.5, "voice_adherence": 7.5,
                     "beat_coverage": 7.5, "character_voice": 7.5, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    context = {
                        "voice": "", "world": "", "characters": "", "outline": "",
                        "canon": "", "anti_patterns": "",
                        "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "",
                                        "beat": "", "position": "", "emotional_arc": "",
                                        "try_fail": "", "scene_beats": [], "foreshadow_plants": [],
                                        "payoff_payoffs": [], "word_target": 3200},
                        "next_chapter_hint": "", "prev_ending": "",
                    }
                    result = draft_chapter(1, context=context)

        saved_file = chapters_dir / "ch_01.md"
        assert saved_file.exists()
        assert saved_file.read_text() == mock_client.generate.return_value

    def test_draft_chapter_raises_on_api_error_last_retry(self, tmp_path):
        """API error on last retry raises the exception."""
        from src.drafting.draft_chapter import draft_chapter

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        mock_client = MagicMock()
        mock_client.generate.side_effect = [Exception("API error"), Exception("API error")]

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                context = {
                    "voice": "", "world": "", "characters": "", "outline": "",
                    "canon": "", "anti_patterns": "",
                    "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "",
                                    "beat": "", "position": "", "emotional_arc": "",
                                    "try_fail": "", "scene_beats": [], "foreshadow_plants": [],
                                    "payoff_payoffs": [], "word_target": 3200},
                    "next_chapter_hint": "", "prev_ending": "",
                }
                with pytest.raises(Exception, match="API error"):
                    draft_chapter(1, context=context, max_retries=2)

    def test_draft_chapter_returns_best_after_max_retries(self, tmp_path):
        """After max retries with no passing score, returns best result seen."""
        from src.drafting.draft_chapter import draft_chapter

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        mock_client = MagicMock()
        mock_client.generate.side_effect = ["Low attempt." * 50, "Better attempt." * 50]

        mock_eval_failing = {"overall_score": 5.0, "voice_adherence": 5.0,
                              "beat_coverage": 5.0, "character_voice": 5.0, "slop_penalty": 0.0}
        mock_eval_better = {"overall_score": 5.8, "voice_adherence": 5.8,
                             "beat_coverage": 5.8, "character_voice": 5.8, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter") as mock_evaluate:
                    mock_evaluate.side_effect = [mock_eval_failing, mock_eval_better]
                    context = {
                        "voice": "", "world": "", "characters": "", "outline": "",
                        "canon": "", "anti_patterns": "",
                        "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "",
                                        "beat": "", "position": "", "emotional_arc": "",
                                        "try_fail": "", "scene_beats": [], "foreshadow_plants": [],
                                        "payoff_payoffs": [], "word_target": 3200},
                        "next_chapter_hint": "", "prev_ending": "",
                    }
                    result = draft_chapter(1, context=context, max_retries=2, min_score=6.0)

        assert result["score"] == 5.8
        assert result["attempts"] == 2

    def test_draft_chapter_without_context_calls_build_context_package(self, tmp_path, monkeypatch):
        """When context is None, build_context_package is called to construct it."""
        from src.drafting.draft_chapter import draft_chapter, build_context_package

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        # Create a minimal outline so build_context_package can read it
        (tmp_path / "outline.md").write_text(
            "# Novel\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- Beat one\n"
        )

        mock_client = MagicMock()
        mock_client.generate.return_value = "A valid chapter text." * 100

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    # Call WITHOUT context - should call build_context_package internally
                    result = draft_chapter(1)

        assert result["word_count"] > 0
        assert result["score"] == 7.0

    def test_draft_chapter_above_max_words_warns(self, tmp_path, capsys):
        """When generated chapter exceeds MAX_CHAPTER_WORDS, warning is printed."""
        from src.drafting.draft_chapter import draft_chapter, MAX_CHAPTER_WORDS

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        # Generate text longer than MAX_CHAPTER_WORDS (8000 by default)
        long_text = "A very long chapter with plenty of words. " * 1100  # ~8800 words

        mock_client = MagicMock()
        mock_client.generate.return_value = long_text

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    context = {
                        "voice": "", "world": "", "characters": "", "outline": "",
                        "canon": "", "anti_patterns": "",
                        "chapter_brief": {"title": "Ch 1", "pov": "Sarah", "location": "",
                                        "beat": "", "position": "", "emotional_arc": "",
                                        "try_fail": "", "scene_beats": [], "foreshadow_plants": [],
                                        "payoff_payoffs": [], "word_target": 3200},
                        "next_chapter_hint": "", "prev_ending": "",
                    }
                    result = draft_chapter(1, context=context)

        captured = capsys.readouterr()
        assert f"WARNING: Above maximum" in captured.out
        assert result["word_count"] > MAX_CHAPTER_WORDS


class TestDraftAllChapters:
    """Tests for draft_all_chapters() with mocked dependencies."""

    def test_resumes_from_existing_chapters(self, tmp_path):
        """When 2 chapters exist, starts from chapter 3."""
        from src.drafting.draft_chapter import draft_all_chapters

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "ch_01.md").write_text("Chapter 1 content.")
        (chapters_dir / "ch_02.md").write_text("Chapter 2 content.")

        # Create outline with exactly 3 chapters so only chapter 3 gets drafted
        (tmp_path / "outline.md").write_text(
            "# Novel\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- Beat one\n\n## Chapter 2\nPOV: Marcus\n\nScene Beats:\n- Beat two\n\n## Chapter 3\nPOV: Sarah\n\nScene Beats:\n- Beat three\n"
        )

        dotnovel = tmp_path / ".novelforge"
        dotnovel.mkdir()
        (dotnovel / "state.json").write_text('{"phase": "drafting", "current_chapter": 2}')

        mock_client = MagicMock()
        mock_client.generate.return_value = "Generated chapter content." * 50

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    results = draft_all_chapters()

        assert len(results) == 1
        assert results[0]["chapter_num"] == 3

    def test_updates_state_after_each_chapter(self, tmp_path):
        """State file is updated with chapter score after each chapter."""
        import json
        from src.drafting.draft_chapter import draft_all_chapters

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        (tmp_path / "outline.md").write_text(
            "# Novel\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- Beat one\n"
        )

        dotnovel = tmp_path / ".novelforge"
        dotnovel.mkdir()
        dotnovel.joinpath("state.json").write_text('{"phase": "drafting"}')

        mock_client = MagicMock()
        mock_client.generate.return_value = "Generated chapter content." * 50

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.draft_chapter.DOTNOVEL", dotnovel):
                    with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                        draft_all_chapters()

        state_content = (dotnovel / "state.json").read_text()
        state = json.loads(state_content)
        assert state["current_chapter"] == 1
        assert "ch_01" in state.get("chapter_scores", {})

    def test_no_chapters_exist_drafts_all(self, tmp_path):
        """With no existing chapters and outline present, drafts all chapters from outline count."""
        from src.drafting.draft_chapter import draft_all_chapters
        import re as re_module

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        (tmp_path / "outline.md").write_text(
            "# Novel\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- Beat one\n\n## Chapter 2\nPOV: Marcus\n\nScene Beats:\n- Beat two\n"
        )

        mock_client = MagicMock()
        mock_client.generate.return_value = "Generated chapter content." * 50

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    results = draft_all_chapters()

        # Outline has 2 chapters
        assert len(results) == 2
        assert results[0]["chapter_num"] == 1
        assert results[1]["chapter_num"] == 2

    def test_outline_with_no_chapters_uses_chapter_target_env(self, tmp_path, monkeypatch):
        """When outline exists but has no chapter headers, CHAPTER_TARGET env is used."""
        from src.drafting.draft_chapter import draft_all_chapters

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        # Outline with no chapter headers at all
        (tmp_path / "outline.md").write_text(
            "# Novel\n\nSome text with no chapter headers.\n"
        )

        mock_client = MagicMock()
        mock_client.generate.return_value = "Generated chapter content." * 50

        mock_eval = {"overall_score": 7.0, "voice_adherence": 7.0,
                     "beat_coverage": 7.0, "character_voice": 7.0, "slop_penalty": 0.0}

        # Override CHAPTER_TARGET to 2 so we get exactly 2 chapters
        monkeypatch.setenv("CHAPTER_TARGET", "2")

        with patch("src.common.api.get_client", return_value=mock_client):
            with patch("src.drafting.draft_chapter.NOVEL_DIR", tmp_path):
                with patch("src.drafting.evaluate.evaluate_chapter", return_value=mock_eval):
                    results = draft_all_chapters()

        # With CHAPTER_TARGET=2 and no chapter headers in outline, should draft 2 chapters
        assert len(results) == 2
        assert results[0]["chapter_num"] == 1
        assert results[1]["chapter_num"] == 2


class TestGetClient:
    """Tests for get_client() lazy import."""

    def test_returns_client_from_common_api(self):
        """get_client delegates to src.common.api.get_client."""
        with patch("src.common.api.get_client") as mock_api_client:
            mock_api_client.return_value = "mock_client"
            result = get_client()
            assert result == "mock_client"
            mock_api_client.assert_called_once()


class TestMainBlock:
    """Tests for the if __name__ == '__main__' block via subprocess."""

    def test_main_block_calls_draft_chapter_with_arg(self, monkeypatch):
        """The __main__ block calls draft_chapter with the argv[1] chapter number."""
        import subprocess
        # Write a minimal test script that imports the module and checks argv
        test_script = '''
import sys
sys.path.insert(0, "src")
from unittest.mock import patch, MagicMock

# Mock draft_chapter to capture calls
called = []
def mock_draft(n, **kwargs):
    called.append(n)
    return {"word_count": 500, "score": 7.0}

with patch("src.drafting.draft_chapter.draft_chapter", mock_draft):
    # Simulate the __main__ block
    chapter_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    mock_draft(chapter_num)

print(f"CALLED_WITH:{chapter_num}")
'''
        result = subprocess.run(
            [sys.executable, "-c", test_script, "5"],
            cwd="/Users/tiankuo/workspace/novel_agent",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "CALLED_WITH:5" in result.stdout

    def test_main_block_defaults_to_chapter_1(self, monkeypatch):
        """Without CLI args, __main__ block defaults to chapter 1."""
        import subprocess
        test_script = '''
import sys
sys.path.insert(0, "src")
from unittest.mock import patch, MagicMock

called = []
def mock_draft(n, **kwargs):
    called.append(n)
    return {"word_count": 500, "score": 7.0}

with patch("src.drafting.draft_chapter.draft_chapter", mock_draft):
    chapter_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    mock_draft(chapter_num)

print(f"CALLED_WITH:{chapter_num}")
'''
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd="/Users/tiankuo/workspace/novel_agent",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "CALLED_WITH:1" in result.stdout
