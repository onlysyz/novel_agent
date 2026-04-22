"""Tests for src/common/prompts.py — prompt building utilities."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.prompts import (
    build_world_prompt,
    build_characters_prompt,
    build_outline_prompt,
    build_canon_prompt,
    build_voice_prompt,
    read_seed,
    read_language,
    read_layer,
    read_anti_patterns,
    read_craft_guide,
    _get_language_instruction,
    LANGUAGE_NAMES,
)


# =============================================================================
# read_seed
# =============================================================================

class TestReadSeed:
    """Tests for read_seed()."""

    def test_returns_content_from_novel_dir(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("A story about dragons.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_seed()
        assert result == "A story about dragons."

    def test_falls_back_to_dotnovel(self, tmp_path):
        dotnovel = tmp_path / ".novelforge"
        dotnovel.mkdir()
        seed_file = dotnovel / "seed.txt"
        seed_file.write_text("Fallback seed content.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path / "nonexistent"):
            with patch("src.common.prompts.DOTNOVEL", dotnovel):
                result = read_seed()
        assert result == "Fallback seed content."

    def test_strips_language_header(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("[language: zh]\n\n这是一个故事。")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_seed()
        assert result == "这是一个故事。"
        assert "language" not in result.lower()

    def test_strips_language_header_no_following_blank_line(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("[language: ja]\nA Japanese story.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_seed()
        assert result == "A Japanese story."

    def test_returns_plain_content_without_header(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("Plain story without language header.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_seed()
        assert result == "Plain story without language header."

    def test_returns_empty_string_when_no_file(self, tmp_path):
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_seed()
        assert result == ""

    def test_strips_whitespace(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("  \n\n  Seed with whitespace  \n  ")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_seed()
        assert result == "Seed with whitespace"


# =============================================================================
# read_language
# =============================================================================

class TestReadLanguage:
    """Tests for read_language()."""

    def test_extracts_language_from_header(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("[language: zh]\n\nStory content here.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_language()
        assert result == "zh"

    def test_defaults_to_en_when_no_header(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("Story without language header.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_language()
        assert result == "en"

    def test_defaults_to_en_when_file_not_found(self, tmp_path):
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_language()
        assert result == "en"

    def test_handles_whitespace_in_language(self, tmp_path):
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("[language:  ja  ]\n\nContent.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_language()
        assert result == "ja"


# =============================================================================
# read_layer
# =============================================================================

class TestReadLayer:
    """Tests for read_layer()."""

    def test_reads_file_from_novel_dir(self, tmp_path):
        world_file = tmp_path / "world.md"
        world_file.write_text("# World\n\nA detailed world.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_layer("world.md")
        assert result == "# World\n\nA detailed world."

    def test_strips_trailing_whitespace(self, tmp_path):
        file = tmp_path / "voice.md"
        file.write_text("  \nVoice content  \n  ")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_layer("voice.md")
        assert result == "Voice content"

    def test_falls_back_to_dotnovel(self, tmp_path):
        dotnovel = tmp_path / ".novelforge"
        dotnovel.mkdir()
        world_file = dotnovel / "world.md"
        world_file.write_text("From dotnovel.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path / "nonexistent"):
            with patch("src.common.prompts.DOTNOVEL", dotnovel):
                result = read_layer("world.md")
        assert result == "From dotnovel."

    def test_returns_empty_string_when_not_found(self, tmp_path):
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_layer("nonexistent.md")
        assert result == ""


# =============================================================================
# read_anti_patterns
# =============================================================================

class TestReadAntiPatterns:
    """Tests for read_anti_patterns()."""

    def test_reads_anti_patterns_file(self, tmp_path):
        ap_file = tmp_path / "ANTI-PATTERNS.md"
        ap_file.write_text("No fake emotion.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_anti_patterns()
        assert result == "No fake emotion."

    def test_returns_empty_when_file_missing(self, tmp_path):
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_anti_patterns()
        assert result == ""


# =============================================================================
# read_craft_guide
# =============================================================================

class TestReadCraftGuide:
    """Tests for read_craft_guide()."""

    def test_reads_craft_file(self, tmp_path):
        craft_file = tmp_path / "CRAFT.md"
        craft_file.write_text("Show don't tell.")
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_craft_guide()
        assert result == "Show don't tell."

    def test_returns_empty_when_file_missing(self, tmp_path):
        with patch("src.common.prompts.NOVEL_DIR", tmp_path):
            result = read_craft_guide()
        assert result == ""


# =============================================================================
# _get_language_instruction
# =============================================================================

class TestGetLanguageInstruction:
    """Tests for _get_language_instruction()."""

    def test_returns_empty_for_english(self):
        result = _get_language_instruction("en")
        assert result == ""

    def test_includes_chinese_for_zh(self):
        result = _get_language_instruction("zh")
        assert "Chinese" in result

    def test_includes_japanese_for_ja(self):
        result = _get_language_instruction("ja")
        assert "Japanese" in result

    def test_includes_korean_for_ko(self):
        result = _get_language_instruction("ko")
        assert "Korean" in result

    def test_includes_spanish_for_es(self):
        result = _get_language_instruction("es")
        assert "Spanish" in result

    def test_includes_french_for_fr(self):
        result = _get_language_instruction("fr")
        assert "French" in result

    def test_includes_german_for_de(self):
        result = _get_language_instruction("de")
        assert "German" in result

    def test_defaults_to_english_for_unknown(self):
        result = _get_language_instruction("xx")
        assert "English" in result


# =============================================================================
# build_world_prompt
# =============================================================================

class TestBuildWorldPrompt:
    """Tests for build_world_prompt()."""

    def test_returns_tuple(self):
        system, user = build_world_prompt("A seed")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_novel_architect(self):
        system, _ = build_world_prompt("A seed")
        assert "novel architect" in system

    def test_user_contains_seed(self):
        _, user = build_world_prompt("A seed about dragons")
        assert "A seed about dragons" in user

    def test_user_contains_requirements(self):
        _, user = build_world_prompt("A seed")
        assert "Geography" in user
        assert "Magic Systems" in user
        assert "Anti-Patterns" in user

    def test_includes_voice_when_provided(self):
        _, user = build_world_prompt("A seed", voice="Dark and gritty.")
        assert "Voice Reference" in user
        assert "Dark and gritty" in user

    def test_excludes_voice_when_none(self):
        _, user = build_world_prompt("A seed", voice=None)
        assert "Voice Reference" not in user

    def test_includes_craft_when_provided(self):
        _, user = build_world_prompt("A seed", craft="Show don't tell.")
        assert "Craft Guidelines" in user
        assert "Show don't tell" in user

    def test_excludes_craft_when_none(self):
        _, user = build_world_prompt("A seed", craft=None)
        assert "Craft Guidelines" not in user

    def test_includes_language_instruction_for_chinese(self):
        _, user = build_world_prompt("A seed", language="zh")
        assert "Simplified Chinese" in user

    def test_excludes_language_for_english(self):
        _, user = build_world_prompt("A seed", language="en")
        assert "Language" not in user

    def test_target_word_count_in_user(self):
        _, user = build_world_prompt("A seed")
        assert "3000-4000 words" in user


# =============================================================================
# build_characters_prompt
# =============================================================================

class TestBuildCharactersPrompt:
    """Tests for build_characters_prompt()."""

    def test_returns_tuple(self):
        system, user = build_characters_prompt("A seed", "A world")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_character_architect(self):
        system, _ = build_characters_prompt("A seed", "A world")
        assert "character architect" in system

    def test_user_contains_seed(self):
        _, user = build_characters_prompt("A seed", "A world")
        assert "A seed" in user

    def test_user_contains_world(self):
        _, user = build_characters_prompt("A seed", "A world")
        assert "A world" in user

    def test_user_contains_requirements(self):
        _, user = build_characters_prompt("A seed", "A world")
        assert "Psychological Profile" in user
        assert "Speech Patterns" in user
        assert "Character Voice Principles" in user

    def test_includes_voice_when_provided(self):
        _, user = build_characters_prompt("A seed", "A world", voice="Literary style.")
        assert "Voice Reference" in user
        assert "Literary style" in user

    def test_excludes_voice_when_none(self):
        _, user = build_characters_prompt("A seed", "A world", voice=None)
        assert "Voice Reference" not in user

    def test_includes_language_for_chinese(self):
        _, user = build_characters_prompt("A seed", "A world", language="zh")
        assert "Simplified Chinese" in user

    def test_character_count_range(self):
        _, user = build_characters_prompt("A seed", "A world")
        assert "3-8 major characters" in user


# =============================================================================
# build_outline_prompt
# =============================================================================

class TestBuildOutlinePrompt:
    """Tests for build_outline_prompt()."""

    def test_returns_tuple(self):
        system, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_save_the_cat(self):
        system, _ = build_outline_prompt("A seed", "A world", "Some characters")
        assert "Save the Cat" in system

    def test_user_contains_seed(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert "A seed" in user

    def test_user_contains_world(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert "A world" in user

    def test_user_contains_characters(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert "Some characters" in user

    def test_user_contains_structure_requirements(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert "FOUR ACTS" in user
        assert "Act I" in user
        assert "Act II" in user

    def test_user_contains_per_chapter_requirements(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert "POV Character" in user
        assert "Save the Cat Beat" in user
        assert "Foreshadowing Plants" in user

    def test_user_contains_foreshadowing_ledger(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters")
        assert "Foreshadowing Ledger" in user

    def test_includes_voice_when_provided(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters",
                                        voice="Formal tone.")
        assert "Voice Reference" in user
        assert "Formal tone" in user

    def test_excludes_voice_when_none(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters", voice=None)
        assert "Voice Reference" not in user

    def test_includes_mystery_when_provided(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters",
                                        mystery="Who killed the king?")
        assert "Central Mystery/Conflict" in user
        assert "Who killed the king" in user

    def test_excludes_mystery_when_none(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters", mystery=None)
        assert "Mystery" not in user

    def test_includes_language_for_chinese(self):
        _, user = build_outline_prompt("A seed", "A world", "Some characters", language="zh")
        assert "Simplified Chinese" in user

    def test_chapter_count_in_system(self):
        system, _ = build_outline_prompt("A seed", "A world", "Some characters")
        assert "22-26 chapters" in system


# =============================================================================
# build_canon_prompt
# =============================================================================

class TestBuildCanonPrompt:
    """Tests for build_canon_prompt()."""

    def test_returns_tuple(self):
        system, user = build_canon_prompt("A seed", "A world", "Characters", "Outline")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_continuity_architect(self):
        system, _ = build_canon_prompt("A seed", "A world", "Characters", "Outline")
        assert "continuity architect" in system

    def test_user_contains_all_inputs(self):
        _, user = build_canon_prompt("A seed", "A world", "Characters", "Outline")
        assert "A seed" in user
        assert "A world" in user
        assert "Characters" in user
        assert "Outline" in user

    def test_user_contains_requirements(self):
        _, user = build_canon_prompt("A seed", "A world", "Characters", "Outline")
        assert "Character Facts" in user
        assert "Political Facts" in user
        assert "Timeline" in user
        assert "Magic Rules" in user

    def test_includes_language_for_japanese(self):
        _, user = build_canon_prompt("A seed", "A world", "Characters", "Outline", language="ja")
        assert "Japanese" in user


# =============================================================================
# build_voice_prompt
# =============================================================================

class TestBuildVoicePrompt:
    """Tests for build_voice_prompt()."""

    def test_returns_tuple(self):
        system, user = build_voice_prompt(["Sample text one.", "Sample text two."], "A seed")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_literary_analyst(self):
        system, _ = build_voice_prompt(["Sample text one."], "A seed")
        assert "literary analyst" in system

    def test_user_contains_seed(self):
        _, user = build_voice_prompt(["Sample text one."], "A seed about war")
        assert "A seed about war" in user

    def test_user_contains_sample_texts_formatted(self):
        _, user = build_voice_prompt(["First sample.", "Second sample."], "A seed")
        assert "Sample 1" in user
        assert "First sample" in user
        assert "Sample 2" in user
        assert "Second sample" in user

    def test_user_contains_voice_characteristics(self):
        _, user = build_voice_prompt(["A sample."], "A seed")
        assert "Sentence Rhythm" in user
        assert "Vocabulary Wells" in user
        assert "POV Characteristics" in user
        assert "Dialogue Style" in user

    def test_multiple_samples_numbered(self):
        _, user = build_voice_prompt(["One", "Two", "Three"], "A seed")
        assert "Sample 1" in user
        assert "Sample 2" in user
        assert "Sample 3" in user

    def test_empty_sample_list_handled(self):
        _, user = build_voice_prompt([], "A seed")
        assert "Sample Texts" in user

    def test_single_sample_works(self):
        _, user = build_voice_prompt(["Only one sample."], "A seed")
        assert "Sample 1" in user
        assert "Only one sample" in user

    def test_includes_language_for_chinese(self):
        _, user = build_voice_prompt(["Sample text."], "A seed", language="zh")
        assert "Simplified Chinese" in user


# =============================================================================
# LANGUAGE_NAMES
# =============================================================================

class TestLanguageNames:
    """Tests for LANGUAGE_NAMES constant."""

    def test_all_expected_languages_present(self):
        assert LANGUAGE_NAMES["en"] == "English"
        assert LANGUAGE_NAMES["zh"] == "Simplified Chinese"
        assert LANGUAGE_NAMES["ja"] == "Japanese"
        assert LANGUAGE_NAMES["ko"] == "Korean"
        assert LANGUAGE_NAMES["es"] == "Spanish"
        assert LANGUAGE_NAMES["fr"] == "French"
        assert LANGUAGE_NAMES["de"] == "German"
