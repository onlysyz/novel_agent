"""Integration tests for run_pipeline.py — full phase orchestration.

Covers normal paths and exception/error paths for:
- Foundation phase (world, characters, outline, canon, voice)
- Drafting phase (chapter writing)
- Review phase
- Export phase
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_novedir(tmp_path):
    """Set up a minimal novel directory with seed.txt."""
    seed = tmp_path / "seed.txt"
    seed.write_text("A retired assassin is forced back into service when her daughter is kidnapped.")
    return tmp_path


@pytest.fixture
def mock_novedir_with_foundation(tmp_path):
    """Set up novel directory with all foundation files already generated."""
    seed = tmp_path / "seed.txt"
    seed.write_text("A detective hunts a serial killer in 1940s Los Angeles.")

    files = {
        "voice.md": "# Voice\n\nHardboiled, Raymond Chandler style.",
        "world.md": "# World\n\n1940s Los Angeles, noir atmosphere.",
        "characters.md": "# Characters\n\n## Detective Mills\nA cynical private eye.",
        "outline.md": """# Outline

## Chapter 1: The Case Begins
POV: Mills
Beat: Setup
Scene Beats:
- Mills receives the case
- The victim's body is found

## Chapter 2: The Trail
POV: Mills
Beat: Fun and Games
Scene Beats:
- Mills follows the clues
""",
        "canon.md": "# Canon\n\nThe war ended three years ago.",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content)

    dotnovel = tmp_path / ".novelforge"
    dotnovel.mkdir()
    dotnovel.joinpath("state.json").write_text(json.dumps({
        "phase": "drafting",
        "started_at": "2024-01-01T00:00:00",
        "completed_phases": ["foundation"],
        "foundation": {
            "world": {"score": 8.0, "iterations": 1},
            "characters": {"score": 8.0, "iterations": 1},
            "outline": {"score": 8.0, "iterations": 1},
            "canon": {"score": 8.0, "iterations": 1},
            "voice": {"score": 8.0, "iterations": 1},
        },
    }))

    return tmp_path


@pytest.fixture
def mock_novedir_with_chapters(tmp_path):
    """Set up novel directory with foundation + chapters ready for review/export."""
    seed = tmp_path / "seed.txt"
    seed.write_text("A detective hunts a serial killer in 1940s Los Angeles.")

    files = {
        "voice.md": "# Voice\n\nHardboiled style.",
        "world.md": "# World\n\n1940s Los Angeles.",
        "characters.md": "# Characters\n\n## Detective Mills\nA cynical private eye.",
        "outline.md": """# Outline

## Chapter 1: The Case Begins
POV: Mills
Beat: Setup
Scene Beats:
- Mills receives the case

## Chapter 2: The Trail
POV: Mills
Beat: Fun and Games
Scene Beats:
- Mills follows the clues
""",
        "canon.md": "# Canon\n\nThe war ended three years ago.",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content)

    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch_01.md").write_text("Chapter one content. " * 200)
    (chapters_dir / "ch_02.md").write_text("Chapter two content. " * 200)

    dotnovel = tmp_path / ".novelforge"
    dotnovel.mkdir()
    dotnovel.joinpath("state.json").write_text(json.dumps({
        "phase": "review",
        "started_at": "2024-01-01T00:00:00",
        "completed_phases": ["foundation", "drafting"],
        "foundation": {
            "world": {"score": 8.0, "iterations": 1},
            "characters": {"score": 8.0, "iterations": 1},
            "outline": {"score": 8.0, "iterations": 1},
            "canon": {"score": 8.0, "iterations": 1},
            "voice": {"score": 8.0, "iterations": 1},
        },
        "drafting": {
            "current_chapter": 2,
            "chapter_scores": {"ch_01": 7.5, "ch_02": 7.0},
            "total_words": 800,
            "total_attempts": 2,
        },
    }))

    return tmp_path


# ─── Foundation Phase Tests ──────────────────────────────────────────────────

class TestFoundationPhaseNormal:
    """Foundation phase: successful generation path."""

    def test_foundation_generates_all_five_documents(self, mock_novedir):
        import run_pipeline

        mock_novedir.mkdir(parents=True, exist_ok=True)
        (mock_novedir / "seed.txt").write_text("A detective story set in 1940s LA.")

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        def write_file_mock(path, content):
            """Side effect: actually write content to the path like the real function does."""
            path.write_text(content)
            return {"score": 8.0, "iterations": 1, "text": content, "path": path}

        with patch("src.foundation.gen_world.generate_world") as mock_gw:
            with patch("src.foundation.gen_characters.generate_characters") as mock_gc:
                with patch("src.foundation.gen_outline.generate_outline") as mock_go:
                    with patch("src.foundation.gen_canon.generate_canon") as mock_gca:
                        with patch("src.foundation.voice_fingerprint.generate_voice") as mock_gv:
                            mock_gw.side_effect = lambda **kw: write_file_mock(mock_novedir / "world.md", "# World\nA world.")
                            mock_gc.side_effect = lambda **kw: write_file_mock(mock_novedir / "characters.md", "# Characters\nSarah and Marcus.")
                            mock_go.side_effect = lambda **kw: write_file_mock(mock_novedir / "outline.md", "# Outline\n## Chapter 1")
                            mock_gca.side_effect = lambda **kw: write_file_mock(mock_novedir / "canon.md", "# Canon\nFacts.")
                            mock_gv.side_effect = lambda **kw: write_file_mock(mock_novedir / "voice.md", "# Voice\nLiterary style.")

                            state = {"phase": "foundation", "completed_phases": []}
                            results = run_pipeline.run_foundation(state)

        assert "world" in results
        assert "characters" in results
        assert "outline" in results
        assert "canon" in results
        assert "voice" in results
        assert (mock_novedir / "world.md").exists()
        assert (mock_novedir / "characters.md").exists()
        assert (mock_novedir / "outline.md").exists()
        assert (mock_novedir / "canon.md").exists()
        assert (mock_novedir / "voice.md").exists()

    def test_foundation_raises_when_seed_missing(self, mock_novedir):
        import run_pipeline

        (mock_novedir / "seed.txt").unlink()

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        with pytest.raises(FileNotFoundError, match="seed.txt not found"):
            run_pipeline.run_foundation({})


class TestFoundationPhaseExceptions:
    """Foundation phase: error paths."""

    def test_foundation_all_files_written_on_success(self, mock_novedir):
        """When all generators succeed, all five foundation files are written to disk."""
        import run_pipeline

        (mock_novedir / "seed.txt").write_text("A detective story.")

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        def write_file_mock(path, content):
            path.write_text(content)
            return {"score": 8.0, "iterations": 1, "text": content, "path": path}

        with patch("src.foundation.gen_world.generate_world") as mock_gw:
            with patch("src.foundation.gen_characters.generate_characters") as mock_gc:
                with patch("src.foundation.gen_outline.generate_outline") as mock_go:
                    with patch("src.foundation.gen_canon.generate_canon") as mock_gca:
                        with patch("src.foundation.voice_fingerprint.generate_voice") as mock_gv:
                            mock_gw.side_effect = lambda **kw: write_file_mock(mock_novedir / "world.md", "# World\nA world.")
                            mock_gc.side_effect = lambda **kw: write_file_mock(mock_novedir / "characters.md", "# Characters\nSarah.")
                            mock_go.side_effect = lambda **kw: write_file_mock(mock_novedir / "outline.md", "# Outline\n## Chapter 1")
                            mock_gca.side_effect = lambda **kw: write_file_mock(mock_novedir / "canon.md", "# Canon\nFacts.")
                            mock_gv.side_effect = lambda **kw: write_file_mock(mock_novedir / "voice.md", "# Voice\nStyle.")

                            state = {"phase": "foundation", "completed_phases": []}
                            results = run_pipeline.run_foundation(state)

        # All files written
        assert (mock_novedir / "world.md").exists()
        assert (mock_novedir / "characters.md").exists()
        assert (mock_novedir / "outline.md").exists()
        assert (mock_novedir / "canon.md").exists()
        assert (mock_novedir / "voice.md").exists()
        assert results["world"]["score"] == 8.0
        assert results["characters"]["score"] == 8.0

    def test_foundation_continues_on_step_api_error(self, mock_novedir):
        import run_pipeline

        (mock_novedir / "seed.txt").write_text("A detective story.")

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        with patch("src.foundation.gen_world.generate_world") as mock_gw:
            with patch("src.foundation.gen_characters.generate_characters") as mock_gc:
                with patch("src.foundation.gen_outline.generate_outline") as mock_go:
                    with patch("src.foundation.gen_canon.generate_canon") as mock_gca:
                        with patch("src.foundation.voice_fingerprint.generate_voice") as mock_gv:
                            # World fails, characters succeeds
                            mock_gw.side_effect = Exception("World generation failed")
                            mock_gc.return_value = {"score": 8.0, "iterations": 1, "text": "# Characters", "path": mock_novedir / "characters.md"}
                            mock_go.return_value = {"score": 8.0, "iterations": 1, "text": "# Outline", "path": mock_novedir / "outline.md"}
                            mock_gca.return_value = {"score": 8.0, "iterations": 1, "text": "# Canon", "path": mock_novedir / "canon.md"}
                            mock_gv.return_value = {"score": 8.0, "iterations": 1, "text": "# Voice", "path": mock_novedir / "voice.md"}

                            state = {"phase": "foundation", "completed_phases": []}

                            # Should raise when world generation fails completely
                            with pytest.raises(Exception, match="World generation failed"):
                                run_pipeline.run_foundation(state)


# ─── Drafting Phase Tests ────────────────────────────────────────────────────

class TestDraftingPhaseNormal:
    """Drafting phase: successful chapter writing."""

    def test_drafting_calls_draft_chapter_for_each_chapter(self, mock_novedir_with_foundation):
        """Verifies draft_chapter is called once per chapter in the outline."""
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        called_chapters = []

        def mock_chapter(ch_num, context=None, language=None):
            called_chapters.append(ch_num)
            chapters_dir = run_pipeline.NOVEL_DIR / "chapters"
            chapters_dir.mkdir(exist_ok=True)
            (chapters_dir / f"ch_{ch_num:02d}.md").write_text(f"Chapter {ch_num} content.")
            return {
                "chapter_num": ch_num,
                "word_count": 3200,
                "score": 7.5,
                "attempts": 1,
            }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Literary style.",
            "world": "A world.",
            "characters": "Characters.",
            "outline": "Outline.",
            "canon": "Canon.",
            "anti_patterns": "Avoid tropes.",
            "chapter_brief": {
                "title": "The Beginning",
                "pov": "Sarah",
                "location": "Here",
                "beat": "Setup",
                "position": "",
                "emotional_arc": "Determination",
                "try_fail": "Fails",
                "scene_beats": ["Beat one"],
                "foreshadow_plants": [],
                "payoff_payoffs": [],
                "word_target": 3200,
            },
            "next_chapter_hint": "",
            "prev_ending": "",
        }

        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 0,
                "chapter_scores": {},
                "total_words": 0,
                "total_attempts": 0,
            },
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                stats = run_pipeline.run_drafting(state)

        assert len(called_chapters) == 2  # 2 chapters in outline
        assert called_chapters == [1, 2]
        chapters_dir = mock_novedir_with_foundation / "chapters"
        assert (chapters_dir / "ch_01.md").exists()
        assert (chapters_dir / "ch_02.md").exists()

    def test_drafting_resumes_from_existing_chapter(self, mock_novedir_with_foundation):
        import run_pipeline

        chapters_dir = mock_novedir_with_foundation / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "ch_01.md").write_text("Already written chapter 1 content.")

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        mock_chapter = MagicMock()
        mock_chapter.return_value = {
            "chapter_num": 2,
            "word_count": 3100,
            "score": 7.0,
            "attempts": 1,
        }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Literary style.",
            "world": "A world.",
            "characters": "Characters.",
            "outline": "Outline.",
            "canon": "Canon.",
            "anti_patterns": "",
            "chapter_brief": {
                "title": "Chapter 2",
                "pov": "Mills",
                "location": "LA",
                "beat": "Fun and Games",
                "position": "",
                "emotional_arc": "",
                "try_fail": "",
                "scene_beats": [],
                "foreshadow_plants": [],
                "payoff_payoffs": [],
                "word_target": 3200,
            },
            "next_chapter_hint": "",
            "prev_ending": "",
        }

        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 1,
                "chapter_scores": {"ch_01": 7.5},
                "total_words": 3200,
                "total_attempts": 1,
            },
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                stats = run_pipeline.run_drafting(state)

        # Only chapter 2 drafted (chapter 1 already existed)
        assert mock_chapter.call_count == 1
        mock_chapter.assert_called_once()
        assert mock_chapter.call_args[0][0] == 2

    def test_drafting_saves_state_after_each_chapter(self, mock_novedir_with_foundation):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        call_counts = {}

        def mock_chapter(ch_num, context=None, language=None):
            call_counts[ch_num] = call_counts.get(ch_num, 0) + 1
            return {
                "chapter_num": ch_num,
                "word_count": 3200,
                "score": 7.5,
                "attempts": 1,
            }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Style.", "world": "World.", "characters": "Chars.",
            "outline": "Outline.", "canon": "Canon.", "anti_patterns": "",
            "chapter_brief": {
                "title": "Ch", "pov": "X", "location": "X", "beat": "X",
                "position": "", "emotional_arc": "", "try_fail": "",
                "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200,
            },
            "next_chapter_hint": "", "prev_ending": "",
        }

        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 0,
                "chapter_scores": {},
                "total_words": 0,
                "total_attempts": 0,
            },
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                run_pipeline.run_drafting(state)

        # State should have been saved with chapter 2 complete
        state_after = json.loads(run_pipeline.STATE_FILE.read_text())
        assert state_after["drafting"]["current_chapter"] == 2


class TestDraftingPhaseExceptions:
    """Drafting phase: error paths."""

    def test_drafting_api_timeout_continues_to_next_chapter(self, mock_novedir_with_foundation):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        call_count = {}

        def mock_chapter(ch_num, context=None, language=None):
            call_count[ch_num] = call_count.get(ch_num, 0) + 1
            if ch_num == 1:
                raise TimeoutError("API request timed out after 3 attempts")
            return {
                "chapter_num": ch_num,
                "word_count": 3200,
                "score": 7.5,
                "attempts": 1,
            }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Style.", "world": "World.", "characters": "Chars.",
            "outline": "Outline.", "canon": "Canon.", "anti_patterns": "",
            "chapter_brief": {
                "title": "Ch", "pov": "X", "location": "X", "beat": "X",
                "position": "", "emotional_arc": "", "try_fail": "",
                "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200,
            },
            "next_chapter_hint": "", "prev_ending": "",
        }

        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 0,
                "chapter_scores": {},
                "total_words": 0,
                "total_attempts": 0,
            },
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                stats = run_pipeline.run_drafting(state)

        # Chapter 1 failed, chapter 2 succeeded
        assert call_count[1] == 1
        assert call_count[2] == 1

    def test_drafting_quota_exceeded_logs_error_and_continues(self, mock_novedir_with_foundation):
        """API quota exceeded on first chapter - error is logged but continues to next chapter."""
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        call_count = {}

        def mock_chapter(ch_num, context=None, language=None):
            call_count[ch_num] = call_count.get(ch_num, 0) + 1
            if ch_num == 1:
                raise RuntimeError("API quota exceeded. Please check your Anthropic account usage at https://console.anthropic.com/")
            return {
                "chapter_num": ch_num,
                "word_count": 3200,
                "score": 7.5,
                "attempts": 1,
            }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Style.", "world": "World.", "characters": "Chars.",
            "outline": "Outline.", "canon": "Canon.", "anti_patterns": "",
            "chapter_brief": {
                "title": "Ch", "pov": "X", "location": "X", "beat": "X",
                "position": "", "emotional_arc": "", "try_fail": "",
                "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200,
            },
            "next_chapter_hint": "", "prev_ending": "",
        }

        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 0,
                "chapter_scores": {},
                "total_words": 0,
                "total_attempts": 0,
            },
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                stats = run_pipeline.run_drafting(state)

        # Chapter 1 failed with quota error, chapter 2 succeeded
        assert call_count[1] == 1
        assert call_count[2] == 1
        # State reflects that chapter 2 was the last attempted (chapter 1 failed silently)
        saved_state = json.loads(run_pipeline.STATE_FILE.read_text())
        assert saved_state["drafting"]["current_chapter"] == 2
        # Chapter 1 has no score since it failed
        assert "ch_01" not in saved_state["drafting"]["chapter_scores"]

    def test_drafting_context_too_long_logs_error_and_continues(self, mock_novedir_with_foundation):
        """Context too long on first chapter - error is logged but continues to next chapter."""
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        call_count = {}

        def mock_chapter(ch_num, context=None, language=None):
            call_count[ch_num] = call_count.get(ch_num, 0) + 1
            if ch_num == 1:
                raise ValueError("Content too long for model context. Please reduce input size.")
            return {
                "chapter_num": ch_num,
                "word_count": 3200,
                "score": 7.5,
                "attempts": 1,
            }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Style.", "world": "World.", "characters": "Chars.",
            "outline": "Outline.", "canon": "Canon.", "anti_patterns": "",
            "chapter_brief": {
                "title": "Ch", "pov": "X", "location": "X", "beat": "X",
                "position": "", "emotional_arc": "", "try_fail": "",
                "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200,
            },
            "next_chapter_hint": "", "prev_ending": "",
        }

        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 0,
                "chapter_scores": {},
                "total_words": 0,
                "total_attempts": 0,
            },
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                stats = run_pipeline.run_drafting(state)

        # Chapter 1 failed with context error, chapter 2 succeeded
        assert call_count[1] == 1
        assert call_count[2] == 1


# ─── Review Phase Tests ─────────────────────────────────────────────────────

class TestReviewPhaseNormal:
    """Review phase: successful revision."""

    def test_review_runs_all_three_steps(self, mock_novedir_with_chapters):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_chapters
        run_pipeline.DOTNOVEL = mock_novedir_with_chapters / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        mock_adversarial = MagicMock()
        mock_adversarial.return_value = {
            "total_cuts": 100,
            "final_text": "Revised chapter text.",
        }

        mock_reader = MagicMock()
        mock_reader.return_value = {
            "average_rating": 4.2,
            "comments": [],
        }

        mock_opus = MagicMock()
        mock_opus.return_value = {
            "final_rating": 4.5,
            "final_review": {"stop_reason": "threshold"},
        }

        state = {
            "phase": "review",
            "completed_phases": ["foundation", "drafting"],
            "drafting": {
                "chapter_scores": {"ch_01": 7.5, "ch_02": 7.0},
            },
            "review": {
                "revision_cycles": 0,
                "chapters_reviewed": [],
            },
        }

        with patch("src.review.adversarial_edit.run_adversarial_loop", mock_adversarial):
            with patch("src.review.reader_panel.run_reader_panel", mock_reader):
                with patch("src.review.review.run_opus_review_loop", mock_opus):
                    with patch("src.drafting.draft_chapter.build_context_package", MagicMock(return_value={})):
                        stats = run_pipeline.run_review(state)

        assert mock_adversarial.call_count == 2
        assert mock_reader.call_count == 2
        assert mock_opus.call_count == 2


class TestReviewPhaseExceptions:
    """Review phase: error paths."""

    def test_review_no_chapters_returns_empty(self, mock_novedir_with_foundation):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        state = {
            "phase": "review",
            "completed_phases": ["foundation"],
            "drafting": {"chapter_scores": {}},
            "review": {"revision_cycles": 0, "chapters_reviewed": []},
        }

        result = run_pipeline.run_review(state)
        assert result == {}


# ─── Export Phase Tests ──────────────────────────────────────────────────────

class TestExportPhaseNormal:
    """Export phase: successful export."""

    def test_export_creates_manuscript_and_results(self, mock_novedir_with_chapters):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_chapters
        run_pipeline.DOTNOVEL = mock_novedir_with_chapters / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        mock_export_all = MagicMock()
        mock_export_all.return_value = {
            "txt": {"txt_path": "export/manuscript.txt"},
            "epub": {"epub_path": "export/manuscript.epub"},
        }

        state = {
            "phase": "export",
            "completed_phases": ["foundation", "drafting", "review"],
            "drafting": {
                "chapter_scores": {"ch_01": 7.5, "ch_02": 7.0},
            },
        }

        with patch("src.export.export.export_all", mock_export_all):
            stats = run_pipeline.run_export(state)

        assert (mock_novedir_with_chapters / "manuscript.md").exists()
        assert (mock_novedir_with_chapters / ".novelforge" / "results.tsv").exists()
        assert stats["chapters"] == 2

    def test_export_includes_revised_versions_when_present(self, mock_novedir_with_chapters):
        import run_pipeline

        chapters_dir = mock_novedir_with_chapters / "chapters"
        (chapters_dir / "ch_01_revised.md").write_text("Revised chapter 1 content.")

        run_pipeline.NOVEL_DIR = mock_novedir_with_chapters
        run_pipeline.DOTNOVEL = mock_novedir_with_chapters / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        mock_export_all = MagicMock()
        mock_export_all.return_value = {}

        state = {
            "phase": "export",
            "completed_phases": ["foundation", "drafting", "review"],
            "drafting": {"chapter_scores": {"ch_01": 7.5, "ch_02": 7.0}},
        }

        with patch("src.export.export.export_all", mock_export_all):
            run_pipeline.run_export(state)

        manuscript = (mock_novedir_with_chapters / "manuscript.md").read_text()
        assert "Revised chapter 1 content" in manuscript


class TestExportPhaseExceptions:
    """Export phase: error paths."""

    def test_export_no_chapters_returns_empty(self, mock_novedir_with_foundation):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        state = {
            "phase": "export",
            "completed_phases": ["foundation"],
            "drafting": {"chapter_scores": {}},
        }

        result = run_pipeline.run_export(state)
        assert result == {}

    def test_export_error_still_saves_manuscript(self, mock_novedir_with_chapters):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_chapters
        run_pipeline.DOTNOVEL = mock_novedir_with_chapters / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        def mock_export_fail(*args, **kwargs):
            raise RuntimeError("Export service unavailable")

        state = {
            "phase": "export",
            "completed_phases": ["foundation", "drafting", "review"],
            "drafting": {
                "chapter_scores": {"ch_01": 7.5, "ch_02": 7.0},
            },
        }

        with patch("src.export.export.export_all", mock_export_fail):
            stats = run_pipeline.run_export(state)

        # Manuscript should still be saved even if export fails
        assert (mock_novedir_with_chapters / "manuscript.md").exists()
        assert (mock_novedir_with_chapters / ".novelforge" / "results.tsv").exists()


# ─── State Management Tests ──────────────────────────────────────────────────

class TestStateManagement:
    """State persistence and phase management."""

    def test_load_state_returns_defaults_for_missing_keys(self, mock_novedir):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"

        state = run_pipeline.load_state()

        assert "phase" in state
        assert "completed_phases" in state
        assert "foundation" in state
        assert "drafting" in state
        assert "review" in state
        assert "export" in state

    def test_load_state_merges_with_existing_file(self, mock_novedir):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"

        # Write partial state
        run_pipeline.STATE_FILE.write_text(json.dumps({
            "phase": "drafting",
            "started_at": "2024-01-01T00:00:00",
        }))

        state = run_pipeline.load_state()

        # Should have defaults merged in
        assert state["phase"] == "drafting"
        assert "completed_phases" in state
        assert "foundation" in state

    def test_save_and_load_state_preserves_data(self, mock_novedir):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"

        original_state = {
            "phase": "drafting",
            "started_at": "2024-01-01T00:00:00",
            "completed_phases": ["foundation"],
            "foundation": {"world": {"score": 8.0, "iterations": 1}},
            "drafting": {
                "current_chapter": 5,
                "chapter_scores": {"ch_01": 7.5, "ch_02": 7.0},
                "total_words": 6400,
            },
        }

        run_pipeline.save_state(original_state)
        loaded_state = run_pipeline.load_state()

        assert loaded_state["phase"] == "drafting"
        assert loaded_state["drafting"]["current_chapter"] == 5
        assert loaded_state["foundation"]["world"]["score"] == 8.0

    def test_is_phase_complete(self, mock_novedir):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"

        state = {"completed_phases": ["foundation", "drafting"]}

        assert run_pipeline.is_phase_complete(state, "foundation") is True
        assert run_pipeline.is_phase_complete(state, "drafting") is True
        assert run_pipeline.is_phase_complete(state, "review") is False

    def test_get_next_phase(self, mock_novedir):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"

        state = {"completed_phases": ["foundation"]}
        assert run_pipeline.get_next_phase(state) == "drafting"

        state = {"completed_phases": ["foundation", "drafting"]}
        assert run_pipeline.get_next_phase(state) == "review"

        state = {"completed_phases": ["foundation", "drafting", "review", "export"]}
        assert run_pipeline.get_next_phase(state) is None


# ─── Streaming Output Tests ──────────────────────────────────────────────────

class TestStreamingOutput:
    """SSE streaming output functionality."""

    def test_log_progress_writes_sse_format(self, mock_novedir):
        import run_pipeline
        import io
        import sys

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = True

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            run_pipeline.log_progress("foundation", "World generation started", "running")
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert output.startswith("data: ")
        entry = json.loads(output[6:])
        assert entry["phase"] == "foundation"
        assert entry["step"] == "running"
        assert "World generation started" in entry["message"]

    def test_log_progress_writes_jsonl_when_not_streaming(self, mock_novedir):
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir
        run_pipeline.DOTNOVEL = mock_novedir / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        run_pipeline.log_progress("drafting", "Chapter 1 writing", "running")

        assert run_pipeline.PROGRESS_FILE.exists()
        lines = run_pipeline.PROGRESS_FILE.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["phase"] == "drafting"
        assert entry["step"] == "running"


# ─── Failed Chapter Recovery Tests ─────────────────────────────────────────────

class TestFailedChapterRecovery:
    """Chapter-level error recovery: failed_chapters, retry, and resume logic."""

    def test_resume_skips_completed_retries_failed(self, mock_novedir_with_foundation):
        """Resume logic must skip chapters with successful scores but retry failed chapters."""
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        # State: ch_01 done (score 7.5), ch_02 failed (in failed_chapters), ch_03 not started
        state = {
            "phase": "drafting",
            "completed_phases": ["foundation"],
            "drafting": {
                "current_chapter": 2,
                "chapter_scores": {
                    "ch_01": 7.5,
                    "ch_02": 0.0,   # failed - all retries exhausted
                },
                "total_words": 3200,
                "total_attempts": 3,
                "failed_chapters": [2],
                "drafting_errors": {"2": "Max retries exceeded"},
            },
        }
        run_pipeline.save_state(state)

        # Track which chapters are drafted
        drafted = []

        def mock_chapter(ch_num, context=None, language=None):
            drafted.append(ch_num)
            return {
                "chapter_num": ch_num,
                "word_count": 3200,
                "score": 7.0,
                "attempts": 1,
            }

        mock_build_ctx = MagicMock()
        mock_build_ctx.return_value = {
            "voice": "Style.", "world": "World.", "characters": "Chars.",
            "outline": "Outline.", "canon": "Canon.", "anti_patterns": "",
            "chapter_brief": {
                "title": "Ch", "pov": "X", "location": "X", "beat": "X",
                "position": "", "emotional_arc": "", "try_fail": "",
                "scene_beats": [], "foreshadow_plants": [], "payoff_payoffs": [], "word_target": 3200,
            },
            "next_chapter_hint": "", "prev_ending": "",
        }

        with patch("src.drafting.draft_chapter.draft_chapter", mock_chapter):
            with patch("src.drafting.draft_chapter.build_context_package", mock_build_ctx):
                run_pipeline.run_drafting(state)

        # ch_01 was skipped (already scored), ch_02 was retried
        assert drafted == [2]

    def test_drafting_saves_failed_chapter_and_error(self, mock_novedir_with_foundation):
        """When draft_chapter exhausts retries, it saves failed_chapters and drafting_errors."""
        import run_pipeline
        from src.drafting.draft_chapter import _update_drafting_state, _load_state

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        # Set up a clean state
        init_state = {
            "phase": "drafting",
            "drafting": {
                "current_chapter": 0,
                "chapter_scores": {},
                "total_words": 0,
                "total_attempts": 0,
                "failed_chapters": [],
                "drafting_errors": {},
            },
        }
        run_pipeline.save_state(init_state)

        # Simulate _update_drafting_state being called after max retries exceeded
        _update_drafting_state(
            chapter_num=1,
            score=0.0,
            word_count=0,
            attempts=5,
            error="Max retries (5) exceeded",
        )

        state = _load_state()
        assert 1 in state["drafting"]["failed_chapters"]
        assert state["drafting"]["drafting_errors"]["1"] == "Max retries (5) exceeded"
        # Score should be 0 (not removed - it's already 0 for failed chapters)
        assert state["drafting"]["chapter_scores"].get("ch_01") == 0.0

    def test_retry_clears_failed_chapter_and_score(self, mock_novedir_with_foundation):
        """Retrying a chapter removes it from failed_chapters and clears its score."""
        import run_pipeline

        run_pipeline.NOVEL_DIR = mock_novedir_with_foundation
        run_pipeline.DOTNOVEL = mock_novedir_with_foundation / ".novelforge"
        run_pipeline.DOTNOVEL.mkdir(parents=True, exist_ok=True)
        run_pipeline.STATE_FILE = run_pipeline.DOTNOVEL / "state.json"
        run_pipeline.PROGRESS_FILE = run_pipeline.DOTNOVEL / "progress.jsonl"
        run_pipeline.USE_STREAMING = False

        state = {
            "phase": "drafting",
            "drafting": {
                "current_chapter": 2,
                "chapter_scores": {
                    "ch_01": 7.5,
                    "ch_02": 0.0,
                },
                "total_words": 3200,
                "total_attempts": 5,
                "failed_chapters": [2],
                "drafting_errors": {"2": "Max retries exceeded"},
            },
        }
        run_pipeline.save_state(state)

        # Simulate what retry_chapter Tauri command does
        state = run_pipeline.load_state()
        drafting = state.get("drafting", {})
        failed = drafting.get("failed_chapters", [])
        if 2 in failed:
            failed.remove(2)
        scores = drafting.get("chapter_scores", {})
        scores.pop("ch_02", None)
        drafting["current_chapter"] = 1  # chapter_num - 1 so smart resume picks it
        run_pipeline.save_state(state)

        loaded = run_pipeline.load_state()
        assert 2 not in loaded["drafting"]["failed_chapters"]
        assert "ch_02" not in loaded["drafting"]["chapter_scores"]
        assert loaded["drafting"]["current_chapter"] == 1
