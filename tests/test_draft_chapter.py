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

    def test_short_file_returns_full_text(self, tmp_path):
        """File under 2000 chars returned in full."""
        from src.drafting.draft_chapter import get_previous_chapter_ending
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        prev_file = chapters_dir / "ch_01.md"
        prev_file.write_text("A short chapter.")
        result = get_previous_chapter_ending(chapters_dir, 2)
        assert result == "A short chapter."

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
