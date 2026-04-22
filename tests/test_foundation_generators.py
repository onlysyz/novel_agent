"""Tests for src/foundation/ — gen_outline, gen_world, gen_characters, gen_canon."""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# generate_outline tests
# =============================================================================

class TestGenerateOutline:
    """Tests for src.foundation.gen_outline.generate_outline()."""

    def test_returns_result_dict_with_required_keys(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat"
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=mock_result):
                            result = generate_outline(seed="A seed", world="A world",
                                                      characters="Sarah: protagonist")

        assert "text" in result
        assert "score" in result
        assert "iterations" in result
        assert "path" in result
        assert result["score"] == 8.0

    def test_saves_output_to_file(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat"
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist")

        saved = (tmp_path / "outline.md").read_text()
        assert "# Outline" in saved

    def test_raises_when_no_seed_provided_or_found(self, tmp_path):
        import src.foundation.gen_outline as gen_outline_mod

        with patch.object(gen_outline_mod, "read_seed", return_value=""):
            with pytest.raises(ValueError, match="No seed"):
                gen_outline_mod.generate_outline()

    def test_uses_chapter_target_from_env(self, tmp_path, monkeypatch):
        from src.foundation.gen_outline import generate_outline

        monkeypatch.setenv("CHAPTER_TARGET", "10")

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat"
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist")
        # Should complete without error using CHAPTER_TARGET=10
        assert result["score"] == 8.0

    def test_passes_on_first_iteration(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat"
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist")

        assert result["iterations"] == 1
        assert mock_client.generate.call_count == 1

    def test_retries_on_low_score(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            "Low quality outline.",
            "Better outline.",
            "Good enough outline.",
        ]
        failing_result = {"score": 5.0, "passed": False, "feedback": "Too shallow"}
        passing_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", side_effect=[
                            failing_result, failing_result, passing_result
                        ]):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist",
                                                          max_iterations=3)

        assert result["iterations"] == 3
        assert result["score"] == 8.0
        assert mock_client.generate.call_count == 3

    def test_uses_refinement_context_on_retry(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        calls = []
        mock_client = MagicMock()
        mock_client.generate.side_effect = lambda sys, user, **kw: calls.append(user) or "# Outline"
        failing_result = {"score": 5.0, "passed": False, "feedback": "Too shallow"}
        passing_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", side_effect=[
                            failing_result, passing_result
                        ]):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                generate_outline(seed="A seed", world="A world",
                                                 characters="Sarah: protagonist",
                                                 max_iterations=2)

        # Second call should include refinement context
        assert "Previous Attempt Feedback" in calls[1]

    def test_uses_voice_from_read_layer_when_available(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        layer_calls = {}
        mock_client = MagicMock()
        mock_client.generate.return_value = "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat"
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        def capture_layer(filename):
            layer_calls[filename] = filename
            return {"world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                    "voice.md": "Dark and gritty style.",
            }.get(filename, "")

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=capture_layer):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                generate_outline(seed="A seed", world="A world",
                                                 characters="Sarah: protagonist")

        assert "voice.md" in layer_calls

    def test_max_iterations_returns_best_effort(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.return_value = "Best effort outline."
        failing_result = {"score": 5.0, "passed": False, "feedback": "Low score"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=failing_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist",
                                                          max_iterations=2)

        assert result["iterations"] == 2
        assert result["score"] == 5.0
        assert mock_client.generate.call_count == 2

    def test_api_error_continues_iteration(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            Exception("API error"),
            "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat",
        ]
        passing_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=passing_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist",
                                                          max_iterations=2)

        # Second call succeeded after first API error
        assert result["score"] == 8.0
        assert mock_client.generate.call_count == 2

    def test_api_error_on_last_retry_raises(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("Final API error")
        failing_result = {"score": 5.0, "passed": False, "feedback": "Low score"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="en"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=failing_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                with pytest.raises(Exception, match="Final API error"):
                                    generate_outline(seed="A seed", world="A world",
                                                     characters="Sarah: protagonist",
                                                     max_iterations=1)

    def test_reads_language_from_seed_header(self, tmp_path):
        from src.foundation.gen_outline import generate_outline

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Outline\n\n## Chapter 1\nPOV: Sarah\n\nScene Beats:\n- First beat"
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_outline.get_client", return_value=mock_client):
            with patch("src.foundation.gen_outline.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_outline.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                }.get(f, "")):
                    with patch("src.foundation.gen_outline.read_language", return_value="zh"):
                        with patch("src.foundation.gen_outline.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_outline.NOVEL_DIR", tmp_path):
                                result = generate_outline(seed="A seed", world="A world",
                                                          characters="Sarah: protagonist")
        assert result["score"] == 8.0


# =============================================================================
# generate_world tests
# =============================================================================

class TestGenerateWorld:
    """Tests for src.foundation.gen_world.generate_world()."""

    def test_returns_result_dict_with_required_keys(self, tmp_path):
        from src.foundation.gen_world import generate_world

        mock_client = MagicMock()
        mock_client.generate.return_value = "# World\n\nA detailed world bible."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_world.get_client", return_value=mock_client):
            with patch("src.foundation.gen_world.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_world.read_layer", side_effect=lambda f: {
                    "voice.md": "Literary style.",
                }.get(f, "")):
                    with patch("src.foundation.gen_world.read_language", return_value="en"):
                        with patch("src.foundation.gen_world.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_world.NOVEL_DIR", tmp_path):
                                result = generate_world(seed="A seed")

        assert "text" in result
        assert "score" in result
        assert "iterations" in result
        assert "path" in result
        assert result["score"] == 8.0

    def test_saves_to_world_md(self, tmp_path):
        from src.foundation.gen_world import generate_world

        mock_client = MagicMock()
        mock_client.generate.return_value = "# World\n\nA detailed world."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_world.get_client", return_value=mock_client):
            with patch("src.foundation.gen_world.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_world.read_layer", return_value=""):
                    with patch("src.foundation.gen_world.read_language", return_value="en"):
                        with patch("src.foundation.gen_world.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_world.NOVEL_DIR", tmp_path):
                                result = generate_world(seed="A seed")

        assert (tmp_path / "world.md").exists()

    def test_passes_on_first_iteration(self, tmp_path):
        from src.foundation.gen_world import generate_world

        mock_client = MagicMock()
        mock_client.generate.return_value = "# World\n\nA world."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_world.get_client", return_value=mock_client):
            with patch("src.foundation.gen_world.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_world.read_layer", return_value=""):
                    with patch("src.foundation.gen_world.read_language", return_value="en"):
                        with patch("src.foundation.gen_world.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_world.NOVEL_DIR", tmp_path):
                                result = generate_world(seed="A seed")

        assert result["iterations"] == 1
        assert mock_client.generate.call_count == 1

    def test_refines_on_low_score(self, tmp_path):
        from src.foundation.gen_world import generate_world

        mock_client = MagicMock()
        mock_client.generate.side_effect = ["Shallow world.", "Detailed world."]
        failing = {"score": 5.0, "passed": False, "feedback": "Too shallow"}
        passing = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_world.get_client", return_value=mock_client):
            with patch("src.foundation.gen_world.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_world.read_layer", return_value=""):
                    with patch("src.foundation.gen_world.read_language", return_value="en"):
                        with patch("src.foundation.gen_world.score_foundation", side_effect=[failing, passing]):
                            with patch("src.foundation.gen_world.NOVEL_DIR", tmp_path):
                                result = generate_world(seed="A seed", max_iterations=2)

        assert result["iterations"] == 2
        assert result["score"] == 8.0



# =============================================================================
# generate_characters tests
# =============================================================================

class TestGenerateCharacters:
    """Tests for src.foundation.gen_characters.generate_characters()."""

    def test_returns_result_dict_with_required_keys(self, tmp_path):
        from src.foundation.gen_characters import generate_characters

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Characters\n\n## Sarah\nA protagonist."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_characters.get_client", return_value=mock_client):
            with patch("src.foundation.gen_characters.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_characters.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "voice.md": "Literary style.",
                }.get(f, "")):
                    with patch("src.foundation.gen_characters.read_language", return_value="en"):
                        with patch("src.foundation.gen_characters.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_characters.NOVEL_DIR", tmp_path):
                                result = generate_characters(seed="A seed", world="A world")

        assert "text" in result
        assert "score" in result
        assert "iterations" in result
        assert "path" in result
        assert result["score"] == 8.0

    def test_saves_to_characters_md(self, tmp_path):
        from src.foundation.gen_characters import generate_characters

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Characters\n\n## Sarah\nA protagonist."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_characters.get_client", return_value=mock_client):
            with patch("src.foundation.gen_characters.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_characters.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                }.get(f, "")):
                    with patch("src.foundation.gen_characters.read_language", return_value="en"):
                        with patch("src.foundation.gen_characters.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_characters.NOVEL_DIR", tmp_path):
                                result = generate_characters(seed="A seed", world="A world")

        assert (tmp_path / "characters.md").exists()

    def test_passes_on_first_iteration(self, tmp_path):
        from src.foundation.gen_characters import generate_characters

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Characters\n\n## Sarah\nA protagonist."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_characters.get_client", return_value=mock_client):
            with patch("src.foundation.gen_characters.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_characters.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                }.get(f, "")):
                    with patch("src.foundation.gen_characters.read_language", return_value="en"):
                        with patch("src.foundation.gen_characters.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_characters.NOVEL_DIR", tmp_path):
                                result = generate_characters(seed="A seed", world="A world")

        assert result["iterations"] == 1

    def test_retries_on_low_score(self, tmp_path):
        from src.foundation.gen_characters import generate_characters

        mock_client = MagicMock()
        mock_client.generate.side_effect = ["Flat characters.", "Distinct characters."]
        failing = {"score": 5.0, "passed": False, "feedback": "Not distinct enough"}
        passing = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_characters.get_client", return_value=mock_client):
            with patch("src.foundation.gen_characters.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_characters.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                }.get(f, "")):
                    with patch("src.foundation.gen_characters.read_language", return_value="en"):
                        with patch("src.foundation.gen_characters.score_foundation", side_effect=[failing, passing]):
                            with patch("src.foundation.gen_characters.NOVEL_DIR", tmp_path):
                                result = generate_characters(seed="A seed", world="A world", max_iterations=2)

        assert result["iterations"] == 2
        assert result["score"] == 8.0

    def test_refinement_context_added_on_retry(self, tmp_path):
        from src.foundation.gen_characters import generate_characters

        user_calls = []
        mock_client = MagicMock()
        mock_client.generate.side_effect = lambda sys, user, **kw: user_calls.append(user) or "# Characters"
        failing = {"score": 5.0, "passed": False, "feedback": "Add more depth"}
        passing = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_characters.get_client", return_value=mock_client):
            with patch("src.foundation.gen_characters.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_characters.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                }.get(f, "")):
                    with patch("src.foundation.gen_characters.read_language", return_value="en"):
                        with patch("src.foundation.gen_characters.score_foundation", side_effect=[failing, passing]):
                            with patch("src.foundation.gen_characters.NOVEL_DIR", tmp_path):
                                generate_characters(seed="A seed", world="A world", max_iterations=2)

        assert "Previous Attempt Feedback" in user_calls[1]


# =============================================================================
# generate_canon tests
# =============================================================================

class TestGenerateCanon:
    """Tests for src.foundation.gen_canon.generate_canon()."""

    def test_returns_result_dict_with_required_keys(self, tmp_path):
        from src.foundation.gen_canon import generate_canon

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Canon\n\n## Character Facts\nSarah: protagonist."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_canon.get_client", return_value=mock_client):
            with patch("src.foundation.gen_canon.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_canon.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                    "outline.md": "# Outline\n\n## Chapter 1",
                }.get(f, "")):
                    with patch("src.foundation.gen_canon.read_language", return_value="en"):
                        with patch("src.foundation.gen_canon.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_canon.NOVEL_DIR", tmp_path):
                                result = generate_canon(seed="A seed", world="A world",
                                                        characters="Sarah: protagonist",
                                                        outline="# Outline")

        assert "text" in result
        assert "score" in result
        assert "iterations" in result
        assert "path" in result
        assert result["score"] == 8.0

    def test_saves_to_canon_md(self, tmp_path):
        from src.foundation.gen_canon import generate_canon

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Canon\n\n## Facts\nA fact."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_canon.get_client", return_value=mock_client):
            with patch("src.foundation.gen_canon.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_canon.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                    "outline.md": "# Outline",
                }.get(f, "")):
                    with patch("src.foundation.gen_canon.read_language", return_value="en"):
                        with patch("src.foundation.gen_canon.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_canon.NOVEL_DIR", tmp_path):
                                result = generate_canon(seed="A seed", world="A world",
                                                        characters="Sarah: protagonist",
                                                        outline="# Outline")

        assert (tmp_path / "canon.md").exists()

    def test_passes_on_first_iteration(self, tmp_path):
        from src.foundation.gen_canon import generate_canon

        mock_client = MagicMock()
        mock_client.generate.return_value = "# Canon\n\n## Facts\nA fact."
        mock_result = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_canon.get_client", return_value=mock_client):
            with patch("src.foundation.gen_canon.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_canon.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                    "outline.md": "# Outline",
                }.get(f, "")):
                    with patch("src.foundation.gen_canon.read_language", return_value="en"):
                        with patch("src.foundation.gen_canon.score_foundation", return_value=mock_result):
                            with patch("src.foundation.gen_canon.NOVEL_DIR", tmp_path):
                                result = generate_canon(seed="A seed", world="A world",
                                                        characters="Sarah: protagonist",
                                                        outline="# Outline")

        assert result["iterations"] == 1

    def test_retries_on_low_score(self, tmp_path):
        from src.foundation.gen_canon import generate_canon

        mock_client = MagicMock()
        mock_client.generate.side_effect = ["Incomplete canon.", "Complete canon."]
        failing = {"score": 5.0, "passed": False, "feedback": "Missing facts"}
        passing = {"score": 8.0, "passed": True, "feedback": "Good"}

        with patch("src.foundation.gen_canon.get_client", return_value=mock_client):
            with patch("src.foundation.gen_canon.read_seed", return_value="A seed"):
                with patch("src.foundation.gen_canon.read_layer", side_effect=lambda f: {
                    "world.md": "A world",
                    "characters.md": "Sarah: protagonist",
                    "outline.md": "# Outline",
                }.get(f, "")):
                    with patch("src.foundation.gen_canon.read_language", return_value="en"):
                        with patch("src.foundation.gen_canon.score_foundation", side_effect=[failing, passing]):
                            with patch("src.foundation.gen_canon.NOVEL_DIR", tmp_path):
                                result = generate_canon(seed="A seed", world="A world",
                                                        characters="Sarah: protagonist",
                                                        outline="# Outline",
                                                        max_iterations=2)

        assert result["iterations"] == 2
        assert result["score"] == 8.0
