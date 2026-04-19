"""Tests for review.py — Opus review parsing and stopping logic."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.review.review import ReviewParser


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
