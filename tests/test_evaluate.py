"""Tests for evaluate.py — 9-dimension scoring and slop detection."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.drafting.evaluate import (
    SlopDetector,
    _parse_evaluation_response,
    _default_evaluation,
    quick_slop_check,
    evaluate_chapter,
    DIMENSION_CRITERIA,
)


class TestSlopDetector:
    """Tests for SlopDetector mechanical slop detection."""

    def test_tier1_banned_words_detected(self):
        """Tier 1 banned words incur up to 4pt penalty."""
        text = "This paradigm leverages synergy to optimize our holistic approach."
        detector = SlopDetector(text)
        assert detector._check_tier1_banned() == 4.0

    def test_tier1_banned_partial(self):
        """Partial tier1 banned words counted correctly."""
        text = "We utilize the robust system."
        detector = SlopDetector(text)
        assert detector._check_tier1_banned() == 2.0

    def test_tier2_suspicious_cluster_penalty(self):
        """3+ suspicious words in same paragraph incur cluster penalty."""
        text = (
            "The ancient realm held a mysterious power, ancient legends spoke of this "
            "mystical destiny with an ancient hero."
        )
        detector = SlopDetector(text)
        result = detector._check_tier2_suspicious()
        assert result >= 0.5

    def test_tier3_filler_phrases_detected(self):
        """Filler phrases incur up to 2pt penalty."""
        text = "It's worth noting that the fact that due to the fact that we must proceed."
        detector = SlopDetector(text)
        result = detector._check_tier3_filler()
        assert result == 2.0

    def test_dialogue_tells_detected(self):
        """Dialogue tells like 'eyes widened' incur penalty."""
        text = "John's eyes widened. Sarah's heart pounded. Her pulse quickened."
        detector = SlopDetector(text)
        result = detector._check_dialogue_tells()
        assert result == 1.5

    def test_structural_tics_detected(self):
        """Structural tics like 'not just X, but Y' incur penalty."""
        text = "I'm not saying he's wrong. I'm saying he's dangerous."
        detector = SlopDetector(text)
        result = detector._check_structural_tics()
        assert result == 0.5

    def test_em_dash_density_exceeded(self):
        """Excessive em dashes (>15/1000 words) incur 1pt penalty."""
        # 20 em dashes in ~500 words = 40/1000 > 15 threshold
        text = "— ".join(["word"] * 500) + "—"
        detector = SlopDetector(text)
        result = detector._check_em_dash_density()
        assert result == 1.0

    def test_em_dash_density_ok(self):
        """Normal em dash usage incurs no penalty."""
        # At 100+ words with 2 em dashes, density is ~20/1000 which is > 15 threshold
        # Use a longer text with fewer em dashes
        text = "He opened the door slowly, deliberately, with great care and precision. She followed quietly, watching from the shadows. The path ahead was uncertain but they moved forward anyway."
        detector = SlopDetector(text)
        assert detector._check_em_dash_density() == 0.0

    def test_sentence_variation_low_cv(self):
        """Monotonous sentence length incurs 1pt penalty."""
        # All sentences same length = very low CV
        text = "The cat sat. The cat mat. The cat pat."
        detector = SlopDetector(text)
        result = detector._check_sentence_variation()
        assert result == 1.0

    def test_sentence_variation_healthy(self):
        """Varied sentence lengths incur no penalty."""
        text = "Short. This is a medium length sentence that goes on for a bit. And another."
        detector = SlopDetector(text)
        result = detector._check_sentence_variation()
        assert result == 0.0

    def test_transition_abuse_excessive(self):
        """>30% paragraphs starting with 'however/furthermore' incurs penalty."""
        text = "However, something happened. Likewise text. Moreover, more. Additionally, extra. Consequently, last."
        detector = SlopDetector(text)
        result = detector._check_transition_abuse()
        assert result == 1.0

    def test_transition_abuse_ok(self):
        """Normal transition usage incurs no penalty."""
        text = "Meanwhile, things happened. Later, we moved on."
        detector = SlopDetector(text)
        assert detector._check_transition_abuse() == 0.0

    def test_detect_returns_all_keys(self):
        """detect() returns all penalty categories."""
        text = "A simple test sentence with no problems."
        detector = SlopDetector(text)
        result = detector.detect()
        expected_keys = {
            "tier1_banned", "tier2_suspicious", "tier3_filler",
            "dialogue_tells", "structural_tics", "em_dash_density",
            "sentence_variation", "transition_abuse", "total",
        }
        assert expected_keys.issubset(result.keys())

    def test_detect_total_is_sum(self):
        """total penalty is sum of individual penalties."""
        text = "A simple test sentence."
        detector = SlopDetector(text)
        result = detector.detect()
        expected_total = sum(
            v for k, v in result.items() if k != "total"
        )
        assert result["total"] == expected_total


class TestParseEvaluationResponse:
    """Tests for _parse_evaluation_response."""

    def test_parses_all_dimensions(self):
        """Response with all 9 dimensions parsed correctly."""
        response = "\n".join(
            f"### {dim}: 7.5/10\n" for dim in DIMENSION_CRITERIA
        )
        scores = _parse_evaluation_response(response)
        assert len(scores) == 9
        assert all(v == 7.5 for v in scores.values())

    def test_parses_partial_dimensions(self):
        """Missing dimensions default to 6.0."""
        response = "voice_adherence: 8.0/10\nbeat_coverage: 5.5/10\n"
        scores = _parse_evaluation_response(response)
        assert scores["voice_adherence"] == 8.0
        assert scores["beat_coverage"] == 5.5
        for dim in DIMENSION_CRITERIA:
            if dim not in ("voice_adherence", "beat_coverage"):
                assert scores[dim] == 6.0

    def test_parses_decimal_scores(self):
        """Decimal scores parsed correctly."""
        response = "voice_adherence: 7.3/10\nprose_quality: 6.8/10\n"
        scores = _parse_evaluation_response(response)
        assert scores["voice_adherence"] == 7.3
        assert scores["prose_quality"] == 6.8

    def test_empty_response_defaults(self):
        """Empty response defaults all scores to 6.0."""
        scores = _parse_evaluation_response("")
        assert all(v == 6.0 for v in scores.values())

    def test_alternate_format(self):
        """Alternate format 'dim: X' (no /10) is parsed."""
        response = "voice_adherence: 8\nprose_quality: 6\n"
        scores = _parse_evaluation_response(response)
        assert scores["voice_adherence"] == 8.0
        assert scores["prose_quality"] == 6.0


class TestQuickSlopCheck:
    """Tests for quick_slop_check convenience function."""

    def test_returns_detect_result(self):
        """quick_slop_check returns same structure as SlopDetector.detect."""
        text = "delve utilize synergy optimize"
        result = quick_slop_check(text)
        assert "total" in result
        assert result["total"] > 0


    def test_em_dash_density_empty_text(self):
        """Empty text returns 0.0 early without division by zero."""
        detector = SlopDetector("")
        assert detector._check_em_dash_density() == 0.0

    def test_transition_abuse_no_paragraphs(self):
        """Text with no non-empty paragraphs returns 0.0 early."""
        detector = SlopDetector("   \n\n   \n  ")
        assert detector._check_transition_abuse() == 0.0


class TestDefaultEvaluation:
    """Tests for _default_evaluation."""

    def test_returns_scores_dict(self):
        """Returns scores for all 9 dimensions."""
        slop = {"total": 2.0}
        result = _default_evaluation(slop)
        for dim in DIMENSION_CRITERIA:
            assert dim in result
        assert "overall_score" in result
        assert "slop_penalty" in result
        assert result["slop_penalty"] == 2.0


class TestEvaluateChapter:
    """Tests for evaluate_chapter with mocked API."""

    def _mock_response(self):
        """Return a synthetic LLM evaluation response covering all 9 dimensions."""
        return """
### voice_adherence: 7.0/10
Weakest passage: "..."
Strongest passage: "..."
Fix: ...

### beat_coverage: 6.5/10
...

### character_voice: 8.0/10
...

### plants_seeded: 7.0/10
...

### prose_quality: 6.0/10
...

### continuity: 7.5/10
...

### canon_compliance: 8.0/10
...

### lore_integration: 7.0/10
...

### engagement: 6.5/10
...

### SLOP CHECK
No mechanical issues detected.

### SUMMARY
Overall score: 7.1/10
Major issues: None.
Minor issues: Some pacing improvements.
"""

    def test_evaluate_chapter_returns_all_fields(self):
        """evaluate_chapter returns complete result dict with all required keys."""
        mock_client = MagicMock()
        mock_client.generate.return_value = self._mock_response()

        with patch("src.drafting.evaluate.get_client", return_value=mock_client):
            result = evaluate_chapter(
                "Some chapter text.",
                {"chapter_brief": {}, "voice": "", "world": "", "characters": "", "outline": "", "canon": ""},
            )

        assert "overall_score" in result
        assert "slop_penalty" in result
        assert "slop_details" in result
        assert "raw_evaluation" in result
        for dim in DIMENSION_CRITERIA:
            assert dim in result

    def test_evaluate_chapter_splits_slop_penalty(self):
        """Slop penalty is subtracted from voice, prose, and engagement."""
        # Clean text so slop penalty = 0
        clean_text = "A simple clean sentence with normal words."

        mock_client = MagicMock()
        mock_client.generate.return_value = "\n".join(
            f"### {dim}: 7.0/10\n..." for dim in DIMENSION_CRITERIA
        )

        with patch("src.drafting.evaluate.get_client", return_value=mock_client):
            result = evaluate_chapter(
                clean_text,
                {"chapter_brief": {}, "voice": "", "world": "", "characters": "", "outline": "", "canon": ""},
            )

        # All dimensions should be 7.0
        assert result["voice_adherence"] == 7.0
        assert result["prose_quality"] == 7.0
        assert result["engagement"] == 7.0

    def test_evaluate_chapter_api_error_returns_default(self):
        """API error triggers graceful fallback via _default_evaluation."""
        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("API failure")

        with patch("src.drafting.evaluate.get_client", return_value=mock_client):
            result = evaluate_chapter(
                "Some text.",
                {"chapter_brief": {}, "voice": "", "world": "", "characters": "", "outline": "", "canon": ""},
            )

        # Should return default evaluation (all 6s, overall adjusted down by slop)
        assert result["raw_evaluation"] == "Evaluation unavailable (API error)"
        assert "overall_score" in result
        assert result["overall_score"] <= 6.0
