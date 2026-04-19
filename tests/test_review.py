"""Tests for review.py — Opus review parsing and stopping logic."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.review.review import ReviewParser, opus_review, run_opus_review_loop


class TestReviewParserStarRating:
    """Tests for parse_star_rating."""

    def test_parses_standard_format(self):
        """Standard 'X/5 stars' format parsed."""
        text = "Rating: 4.5 out of 5 stars"
        assert ReviewParser.parse_star_rating(text) == 4.5

    def test_parses_decimal_rating(self):
        """Decimal ratings parsed."""
        text = "Rating: 3.7 / 5 stars"
        assert ReviewParser.parse_star_rating(text) == 3.7

    def test_parses_10_star_scale_normalized(self):
        """X/10 scale normalized to 5-star scale."""
        text = "Rating: 8.5/10 stars"
        assert ReviewParser.parse_star_rating(text) == 4.25

    def test_parses_plain_rating(self):
        """Plain 'rating: X' parsed."""
        text = "Critic's rating: 4.0"
        assert ReviewParser.parse_star_rating(text) == 4.0

    def test_parses_star_symbol(self):
        """Star symbol format parsed."""
        text = "Overall rating: 3.5 ★"
        assert ReviewParser.parse_star_rating(text) == 3.5

    def test_no_rating_defaults(self):
        """No rating found defaults to 3.0."""
        text = "No rating information here"
        assert ReviewParser.parse_star_rating(text) == 3.0


class TestReviewParserItems:
    """Tests for parse_items."""

    def test_parses_numbered_items(self):
        """Numbered items parsed with content."""
        text = "1. First suggestion about the dialogue.\n2. Second suggestion about pacing.\n3. Third suggestion about prose."
        items = ReviewParser.parse_items(text)
        assert len(items) == 3
        assert items[0]["number"] == 1
        assert "dialogue" in items[0]["content"]

    def test_item_severity_major(self):
        """'must fix'/'critical'/'major' marked as major severity."""
        text = "1. This is a critical issue that must be fixed."
        items = ReviewParser.parse_items(text)
        assert items[0]["severity"] == "major"

    def test_item_severity_minor(self):
        """'minor'/'cosmetic'/'optional' marked as minor severity."""
        text = "1. This is a minor cosmetic issue."
        items = ReviewParser.parse_items(text)
        assert items[0]["severity"] == "minor"

    def test_item_severity_default_moderate(self):
        """Unmarked items default to moderate severity."""
        text = "1. Consider revising the opening passage."
        items = ReviewParser.parse_items(text)
        assert items[0]["severity"] == "moderate"

    def test_item_type_compression(self):
        """'cut'/'trim'/'compress' marked as compression type."""
        text = "1. Cut the repetitive phrase in paragraph two."
        items = ReviewParser.parse_items(text)
        assert items[0]["type"] == "compression"

    def test_item_type_addition(self):
        """'expand'/'add'/'introduce' marked as addition type."""
        text = "1. Add more sensory detail to the scene."
        items = ReviewParser.parse_items(text)
        assert items[0]["type"] == "addition"

    def test_item_type_mechanical(self):
        """'repetitive'/'pattern' marked as mechanical type."""
        text = "1. The repetitive use of similar sentence structures."
        items = ReviewParser.parse_items(text)
        assert items[0]["type"] == "mechanical"

    def test_item_type_structural(self):
        """'rearrange'/'reorder' marked as structural type."""
        text = "1. Rearrange the scene order for better pacing."
        items = ReviewParser.parse_items(text)
        assert items[0]["type"] == "structural"

    def test_item_qualified_hedged(self):
        """Hedged items marked as qualified."""
        text = "1. Perhaps consider revising the ending."
        items = ReviewParser.parse_items(text)
        assert items[0]["qualified"] is True

    def test_item_not_qualified_direct(self):
        """Direct items not marked as qualified."""
        text = "1. Revise the dialogue in scene two."
        items = ReviewParser.parse_items(text)
        assert items[0]["qualified"] is False


class TestReviewParserCountSeverity:
    """Tests for count_severity."""

    def test_counts_all_categories(self):
        """Counts major, moderate, minor correctly."""
        items = [
            {"severity": "major"},
            {"severity": "major"},
            {"severity": "moderate"},
            {"severity": "minor"},
        ]
        result = ReviewParser.count_severity(items)
        assert result["major"] == 2
        assert result["moderate"] == 1
        assert result["minor"] == 1

    def test_empty_list(self):
        """Empty items list returns all zeros."""
        result = ReviewParser.count_severity([])
        assert result == {"major": 0, "moderate": 0, "minor": 0}


class TestReviewParserShouldStop:
    """Tests for should_stop stopping logic."""

    def test_stop_no_issues(self):
        """Empty items returns stop=True."""
        should_stop, reason = ReviewParser.should_stop(3.0, [])
        assert should_stop is True
        assert "No issues" in reason

    def test_stop_high_rating_no_major(self):
        """Rating >= 4.5 with zero major items stops."""
        items = [
            {"severity": "minor", "qualified": True},
            {"severity": "moderate", "qualified": True},
        ]
        should_stop, reason = ReviewParser.should_stop(4.5, items)
        assert should_stop is True

    def test_stop_high_qualified_ratio(self):
        """Rating >= 4.0 with >50% qualified stops."""
        items = [
            {"severity": "moderate", "qualified": True},
            {"severity": "minor", "qualified": True},
        ]
        should_stop, reason = ReviewParser.should_stop(4.0, items)
        assert should_stop is True

    def test_continue_low_rating_with_major(self):
        """Rating < 4.5 with major items continues."""
        items = [
            {"severity": "major", "qualified": False},
            {"severity": "minor", "qualified": False},
            {"severity": "minor", "qualified": False},
        ]
        should_stop, reason = ReviewParser.should_stop(4.0, items)
        assert should_stop is False

    def test_stop_few_items(self):
        """2 or fewer items stops."""
        items = [
            {"severity": "moderate", "qualified": False},
        ]
        should_stop, reason = ReviewParser.should_stop(3.0, items)
        assert should_stop is True

    def test_continue_many_items(self):
        """Many items with no major issues continues."""
        items = [
            {"severity": "minor", "qualified": False},
            {"severity": "moderate", "qualified": False},
            {"severity": "minor", "qualified": False},
            {"severity": "moderate", "qualified": False},
        ]
        should_stop, reason = ReviewParser.should_stop(3.5, items)
        assert should_stop is False

    def test_stop_reason_includes_counts(self):
        """Stop reason includes severity counts."""
        items = [
            {"severity": "major", "qualified": False},
            {"severity": "moderate", "qualified": False},
            {"severity": "minor", "qualified": False},
        ]
        should_stop, reason = ReviewParser.should_stop(3.0, items)
        assert "1 major" in reason
        assert "1 moderate" in reason
        assert "1 minor" in reason


class TestOpusReview:
    """Tests for opus_review with mocked API."""

    def _mock_review_response(self, rating=4.0, qualified=True):
        """Return a synthetic Opus review response."""
        hedge = "Perhaps " if qualified else ""
        return f"""
**CRITIC'S RATING**: {rating}/5 stars

**CRITIC'S ASSESSMENT**:
The chapter demonstrates solid narrative craft with effective tension building.

**PROFESSOR'S SUGGESTIONS**:
{hedge}Consider expanding the interior monologue in the third paragraph.
{hedge}The dialogue in scene two could be tightened.
"""

    def test_opus_review_returns_required_keys(self):
        """opus_review returns dict with all expected fields."""
        mock_client = MagicMock()
        mock_client.generate_with_opus.return_value = self._mock_review_response()

        with patch("src.review.review.get_client", return_value=mock_client):
            result = opus_review(
                "Chapter text here.",
                {"chapter_brief": {}, "voice": "", "canon": ""},
                1,
            )

        assert "rating" in result
        assert "items" in result
        assert "severity" in result
        assert "should_stop" in result
        assert "stop_reason" in result
        assert "raw_review" in result

    def test_opus_review_parses_rating(self):
        """opus_review correctly parses the star rating from LLM response."""
        mock_client = MagicMock()
        mock_client.generate_with_opus.return_value = self._mock_review_response(rating=3.5)

        with patch("src.review.review.get_client", return_value=mock_client):
            result = opus_review(
                "Chapter text.",
                {"chapter_brief": {}, "voice": "", "canon": ""},
                1,
            )

        assert result["rating"] == 3.5

    def test_opus_review_api_error_returns_defaults(self):
        """API error returns graceful fallback."""
        mock_client = MagicMock()
        mock_client.generate_with_opus.side_effect = Exception("API failure")

        with patch("src.review.review.get_client", return_value=mock_client):
            result = opus_review(
                "Chapter text.",
                {"chapter_brief": {}, "voice": "", "canon": ""},
                1,
            )

        assert result["rating"] == 3.0
        assert result["should_stop"] is True
        assert "API error" in result["stop_reason"]


class TestRunOpusReviewLoop:
    """Tests for run_opus_review_loop."""

    def test_runs_single_iteration_when_stopped_early(self):
        """Loop exits after 1 iteration when should_stop=True."""
        # Build results that always return should_stop=True on first call
        mock_results = [
            {
                "rating": 4.5,
                "items": [{"severity": "minor", "qualified": True}],
                "severity": {"major": 0, "moderate": 0, "minor": 1},
                "should_stop": True,
                "stop_reason": "High rating with no major issues",
                "raw_review": "...",
            }
        ]

        with patch("src.review.review.opus_review", side_effect=mock_results):
            result = run_opus_review_loop(
                "Chapter text.",
                {"chapter_brief": {}, "voice": "", "canon": ""},
                1,
                max_iterations=3,
            )

        assert result["iterations"] == 1
        assert result["final_rating"] == 4.5
        assert result["final_review"]["should_stop"] is True

    def test_runs_max_iterations_when_not_stopped(self):
        """Loop runs all iterations when should_stop=False throughout."""
        mock_results = [
            {
                "rating": 3.5,
                "items": [
                    {"severity": "major", "qualified": False},
                    {"severity": "moderate", "qualified": False},
                ],
                "severity": {"major": 1, "moderate": 1, "minor": 0},
                "should_stop": False,
                "stop_reason": "...",
                "raw_review": "...",
            }
        ] * 3

        with patch("src.review.review.opus_review", side_effect=mock_results):
            result = run_opus_review_loop(
                "Chapter text.",
                {"chapter_brief": {}, "voice": "", "canon": ""},
                1,
                max_iterations=3,
            )

        assert result["iterations"] == 3
        assert len(result["results"]) == 3
