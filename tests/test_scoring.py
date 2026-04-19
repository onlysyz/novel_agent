"""Tests for src/common/scoring.py — foundation scoring utilities."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.scoring import extract_score, score_foundation, iteration_summary


class TestIterationSummary:
    """Tests for iteration_summary()."""

    def test_passed_true_shows_checkmark(self):
        """Passed=True shows ✓ PASSED."""
        result = iteration_summary(1, 7.5, True)
        assert "Iteration 1" in result
        assert "7.5" in result
        assert "✓ PASSED" in result

    def test_passed_false_shows_x(self):
        """Passed=False shows ✗ FAILED."""
        result = iteration_summary(2, 5.2, False)
        assert "Iteration 2" in result
        assert "5.2" in result
        assert "✗ FAILED" in result


class TestScoreFoundation:
    """Tests for score_foundation() with mocked API."""

    def test_unknown_type_raises_valueerror(self):
        """Unknown foundation_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown foundation type"):
            score_foundation("some text", "not_a_type")

    def test_score_foundation_calls_api_and_returns_score(self):
        """Calls get_client, returns score >= min_score = passed."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "Score: 7.5"

        with patch("src.common.scoring.get_client", return_value=mock_client):
            result = score_foundation("A solid world bible.", "world", min_score=7.0)

        assert result["score"] == 7.5
        assert result["passed"] is True
        assert "World scored 7.5" in result["feedback"]

    def test_score_below_min_fails(self):
        """Score below min_score returns passed=False."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "Score: 5.5"

        with patch("src.common.scoring.get_client", return_value=mock_client):
            result = score_foundation("Weak outline.", "outline", min_score=7.0)

        assert result["score"] == 5.5
        assert result["passed"] is False

    def test_all_foundation_types_dispatch_correctly(self):
        """Each foundation_type maps to correct criteria in API call."""
        for foundation_type in ["world", "characters", "outline", "canon", "voice"]:
            mock_client = MagicMock()
            mock_client.generate.return_value = "Score: 7.0"

            with patch("src.common.scoring.get_client", return_value=mock_client):
                result = score_foundation("Sample text.", foundation_type, min_score=6.0)

            assert result["score"] == 7.0
            assert result["passed"] is True
    """Tests for extract_score()."""

    def test_parses_decimal_score(self):
        """Decimal number is extracted correctly."""
        assert extract_score("The score is 7.3 according to our analysis.") == 7.3

    def test_parses_integer_score(self):
        """Integer number is extracted correctly."""
        assert extract_score("Final rating: 8") == 8.0

    def test_returns_first_number(self):
        """First number in string is returned, not the largest."""
        assert extract_score("Rated 5.0 but also 9.5 in the summary") == 5.0

    def test_no_number_returns_default(self):
        """String with no number returns default 6.0."""
        assert extract_score("No numeric rating provided here.") == 6.0

    def test_leading_number_not_at_start(self):
        """Number doesn't need to be at the start of the string."""
        assert extract_score("After review: 6.5 was the consensus.") == 6.5
