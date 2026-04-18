"""Chapter Evaluation System.

9-dimension scoring system for evaluating chapter quality.
Includes mechanical slop detection for AI-generated prose patterns.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client

NOVEL_DIR = Path(".")

# Scoring thresholds
MIN_CHAPTER_SCORE = float(os.getenv("MIN_CHAPTER_SCORE", "6.0"))

# Slop detection thresholds
EM_DASH_PER_1000_WORDS_THRESHOLD = 15
MIN_SENTENCE_CV = 0.3  # Coefficient of variation for sentence length


# =============================================================================
# SLOP DETECTION (Mechanical Checks)
# =============================================================================

class SlopDetector:
    """Detects mechanical patterns that indicate AI-generated prose."""

    # Tier 1: Banned words (strong AI signal)
    TIER1_BANNED = {
        "delve", "utilize", "paradigm", "leverage", "synergy",
        "holistic", "robust", "scalable", "streamline", "optimize",
        "empower", "transformative", "game-changer", "cutting-edge",
        "next-generation", "best-in-class", "world-class",
    }

    # Tier 2: Suspicious words (cluster detection)
    TIER2_SUSPICIOUS = {
        "journey", "realm", "ancient", "mysterious", "powerful",
        "ancient", "legendary", "mystical", "sacred", "eternal",
        "destiny", "fate", "prophecy", "chosen one", "ultimate",
    }

    # Tier 3: Filler phrases
    TIER3_FILLER = {
        "it's worth noting that",
        "let's dive into",
        "it goes without saying",
        "needless to say",
        "as mentioned previously",
        "in order to",
        "the fact that",
        "due to the fact that",
    }

    # AI dialogue tells
    DIALOGUE_TELLS = {
        "eyes widened",
        "eyes softened",
        "heart pounded",
        "heart raced",
        "pulse quickened",
        "a knowing smile",
        "a slow smile",
        "a faint smile",
        "a sharp intake of breath",
        "breath caught",
        "stomach fluttered",
        "blood ran cold",
    }

    # Structural AI tics
    STRUCTURAL_TICS = {
        r"i'm not saying .+\. i'm saying .+",
        r"not just .+, but .+",
        r"on one hand .+, on the other hand .+",
    }

    def __init__(self, text: str):
        self.text = text
        self.words = text.split()
        self.word_count = len(self.words)
        self.sentences = self._split_sentences()
        self.sentence_count = len(self.sentences)
        self.paragraphs = text.split("\n\n")
        self.em_dash_count = text.count("—") + text.count("--")

    def _split_sentences(self) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentence_endings = re.compile(r'[.!?]+(?:\s|$)')
        matches = sentence_endings.split(self.text)
        return [s.strip() for s in matches if s.strip()]

    def _count_word_in_text(self, word_set: set) -> int:
        """Count occurrences of words from set in text."""
        text_lower = self.text.lower()
        return sum(1 for word in word_set if word in text_lower)

    def _check_tier1_banned(self) -> float:
        """Check Tier 1 banned words. Max 4pt penalty."""
        count = self._count_word_in_text(self.TIER1_BANNED)
        if count == 0:
            return 0.0
        return min(4.0, count * 1.0)

    def _check_tier2_suspicious(self) -> float:
        """Check Tier 2 suspicious word clusters. Max 2pt penalty."""
        text_lower = self.text.lower()
        count = sum(1 for word in self.TIER2_SUSPICIOUS if word in text_lower)
        # Cluster penalty: if 3+ in same paragraph
        cluster_count = 0
        for para in self.paragraphs:
            para_lower = para.lower()
            para_count = sum(1 for word in self.TIER2_SUSPICIOUS if word in para_lower)
            if para_count >= 3:
                cluster_count += 1
        if cluster_count > 0:
            return min(2.0, cluster_count * 0.5)
        return 0.0

    def _check_tier3_filler(self) -> float:
        """Check filler phrases. Max 2pt penalty."""
        count = 0
        text_lower = self.text.lower()
        for phrase in self.TIER3_FILLER:
            count += text_lower.count(phrase)
        return min(2.0, count * 0.5)

    def _check_dialogue_tells(self) -> float:
        """Check dialogue tells. Max 2pt penalty."""
        count = 0
        text_lower = self.text.lower()
        for tell in self.DIALOGUE_TELLS:
            count += text_lower.count(tell)
        return min(2.0, count * 0.5)

    def _check_structural_tics(self) -> float:
        """Check structural tics. Max 2pt penalty."""
        count = 0
        for tic in self.STRUCTURAL_TICS:
            count += len(re.findall(tic, self.text, re.IGNORECASE))
        return min(2.0, count * 0.5)

    def _check_em_dash_density(self) -> float:
        """Check em dash density. Max 1pt penalty."""
        if self.word_count == 0:
            return 0.0
        density = self.em_dash_count / (self.word_count / 1000)
        if density > EM_DASH_PER_1000_WORDS_THRESHOLD:
            return 1.0
        return 0.0

    def _check_sentence_variation(self) -> float:
        """Check sentence length variation (CV). Max 1pt penalty."""
        if self.sentence_count < 3:
            return 0.0
        lengths = [len(s.split()) for s in self.sentences]
        if lengths:
            mean = sum(lengths) / len(lengths)
            if mean > 0:
                variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
                std_dev = variance ** 0.5
                cv = std_dev / mean
                if cv < MIN_SENTENCE_CV:
                    return 1.0
        return 0.0

    def _check_transition_abuse(self) -> float:
        """Check paragraph opening transitions. Max 1pt penalty."""
        bad_starts = {"however", "furthermore", "moreover", "additionally", "consequently"}
        para_count = len([p for p in self.paragraphs if p.strip()])
        if para_count == 0:
            return 0.0
        bad_count = 0
        for para in self.paragraphs:
            words = para.strip().split()
            if words and words[0].lower().rstrip(".,") in bad_starts:
                bad_count += 1
        ratio = bad_count / para_count
        if ratio > 0.3:
            return 1.0
        return 0.0

    def detect(self) -> dict:
        """Run all slop detection and return penalties."""
        penalties = {
            "tier1_banned": self._check_tier1_banned(),
            "tier2_suspicious": self._check_tier2_suspicious(),
            "tier3_filler": self._check_tier3_filler(),
            "dialogue_tells": self._check_dialogue_tells(),
            "structural_tics": self._check_structural_tics(),
            "em_dash_density": self._check_em_dash_density(),
            "sentence_variation": self._check_sentence_variation(),
            "transition_abuse": self._check_transition_abuse(),
        }
        penalties["total"] = sum(penalties.values())
        return penalties


# =============================================================================
# 9-DIMENSION SCORING
# =============================================================================

DIMENSION_CRITERIA = {
    "voice_adherence": {
        "description": "Does the prose match the defined voice/style?",
        "checks": [
            "Sentence rhythm variation",
            "Vocabulary wells respected",
            "Body-before-emotion principle",
            "POV distance consistent",
        ],
    },
    "beat_coverage": {
        "description": "Did the chapter hit all outline beats?",
        "checks": [
            "All scene beats dramatized",
            "No beats merely mentioned",
            "Foreshadowing planted naturally",
            "Payoffs delivered correctly",
        ],
    },
    "character_voice": {
        "description": "Can characters be identified without dialogue tags?",
        "checks": [
            "Distinct speech patterns",
            "Characters say real things, not just right things",
            "Characters stumble, say wrong things",
            "No generic dialogue",
        ],
    },
    "plants_seeded": {
        "description": "Was foreshadowing placed naturally?",
        "checks": [
            "Not too obvious",
            "Integrated into scene",
            "Multiple reinforcement points",
            "Proper plant-payoff distance",
        ],
    },
    "prose_quality": {
        "description": "Sentence variety, specificity, show-don't-tell?",
        "checks": [
            "3+ consecutive sentences don't start same way",
            "Concrete nouns vs. abstract",
            "Character-experiential metaphors",
            "Show-don't-tell at emotional peaks",
        ],
    },
    "continuity": {
        "description": "Logical and emotional flow from previous chapter?",
        "checks": [
            "Picks up from previous ending",
            "Character state consistent",
            "Timeline consistent",
            "No contradictions",
        ],
    },
    "canon_compliance": {
        "description": "All facts checked against canon.md?",
        "checks": [
            "Character facts accurate",
            "Political/timeline facts accurate",
            "Magic rules followed",
            "No major violations",
        ],
    },
    "lore_integration": {
        "description": "Does the world do work in scenes?",
        "checks": [
            "Not just set dressing",
            "World affects plot",
            "Culture feels authentic",
            "Locations have specific details",
        ],
    },
    "engagement": {
        "description": "Would a reader turn the page?",
        "checks": [
            "Tension source present",
            "Not predictable excellence",
            "Something unexpected",
            "Page-turn drive",
        ],
    },
}


def evaluate_chapter(
    text: str,
    context: dict,
    model: Optional[str] = None,
) -> dict:
    """
    Evaluate a chapter on 9 dimensions with slop detection.

    Args:
        text: Chapter prose to evaluate
        context: Full context package from draft_chapter
        model: Optional model override

    Returns:
        dict with all scores and slop penalty
    """
    client = get_client(model)

    # Run slop detection first
    slop_detector = SlopDetector(text)
    slop_result = slop_detector.detect()

    # Build evaluation prompt
    brief = context.get("chapter_brief", {})
    voice = context.get("voice", "")
    world = context.get("world", "")
    characters = context.get("characters", "")
    outline = context.get("outline", "")
    canon = context.get("canon", "")

    system_prompt = """You are an expert literary critic evaluating a chapter.

You evaluate on 9 dimensions. For each:
1. Score 1-10 (see calibration below)
2. Quote specific passages (weakest + strongest)
3. Give one concrete fix

SCORING CALIBRATION:
- 9-10: Among the best chapters in published fantasy. Compete with named works.
- 7-8: Strong, publishable with editorial polish. Specific flaws don't break experience.
- 5-6: Functional but flat. Needs substantial revision. Generic where specificity needed.
- 3-4: Significant problems: voice breaks, beats missed, prose generic.
- 1-2: Not usable. Rewrite from scratch.

MEDIAN AI SCORE IS 6. A 7 requires something a generic AI draft wouldn't do.
Be demanding. Quote passages. Do not inflate scores."""

    user_prompt = f"""Evaluate this chapter on all 9 dimensions.

## CHAPTER TO EVALUATE
{text[:8000]}

## CHAPTER BRIEF
Title: {brief.get('title', 'Unknown')}
POV: {brief.get('pov', 'Unknown')}
Beat Type: {brief.get('beat', 'Unknown')}
Emotional Arc: {brief.get('emotional_arc', 'Unknown')}
Scene Beats: {', '.join(brief.get('scene_beats', [])) or 'Not specified'}
Foreshadow Plants: {', '.join(brief.get('foreshadow_plants', [])) or 'Not specified'}
Payoffs: {', '.join(brief.get('payoff_payoffs', [])) or 'Not specified'}

## VOICE REFERENCE
{voice[:2000] if voice else 'No voice guide'}

## WORLD CONTEXT
{world[:2000] if world else 'No world context'}

## CHARACTER CONTEXT
{characters[:2000] if characters else 'No character context'}

## CANON FACTS
{canon[:1500] if canon else 'No canonical facts'}

## YOUR TASK

Evaluate on all 9 dimensions. Format your response as:

### voice_adherence: X/10
**Weakest passage**: "..."
**Strongest passage**: "..."
**Fix**: ...

### beat_coverage: X/10
...

(Same for all 9 dimensions)

Then provide:
### SLOP CHECK
Any mechanical issues detected (Tier 1 banned words, dialogue tells, etc.)?

### SUMMARY
Overall score: X.X/10
Major issues (must fix): ...
Minor issues (can fix later): ..."""

    try:
        response = client.generate(system_prompt, user_prompt, max_tokens=4096)
    except Exception as e:
        print(f"Evaluation API error: {e}")
        return _default_evaluation(slop_result)

    # Parse scores from response
    scores = _parse_evaluation_response(response)

    # Apply slop penalty
    slop_penalty = slop_result["total"]
    base_scores = scores.copy()

    for key in ["voice_adherence", "prose_quality", "engagement"]:
        scores[key] = max(1.0, scores.get(key, 6.0) - slop_penalty * 0.3)

    # Calculate overall
    dimension_scores = [v for k, v in scores.items() if k in DIMENSION_CRITERIA]
    overall = sum(dimension_scores) / len(dimension_scores) if dimension_scores else 5.0

    # Major canon violation caps at 6
    if slop_result.get("canon_violation"):
        overall = min(overall, 6.0)

    result = {
        **scores,
        "slop_penalty": slop_penalty,
        "slop_details": slop_result,
        "overall_score": round(overall, 2),
        "raw_evaluation": response,
    }

    return result


def _parse_evaluation_response(response: str) -> dict:
    """Parse dimension scores from LLM evaluation response."""
    scores = {}
    dimensions = list(DIMENSION_CRITERIA.keys())

    # Pattern: "### dimension_name: X/10" or "dimension_name: X/10"
    for dim in dimensions:
        patterns = [
            rf"{dim}:\s*(\d+\.?\d*)\s*/\s*10",
            rf"{dim}\s*:\s*(\d+\.?\d*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                scores[dim] = float(match.group(1))
                break

    # Default missing scores to 6.0
    for dim in dimensions:
        if dim not in scores:
            scores[dim] = 6.0

    return scores


def _default_evaluation(slop_result: dict) -> dict:
    """Return a default evaluation when API fails."""
    scores = {dim: 6.0 for dim in DIMENSION_CRITERIA}
    overall = 6.0 - slop_result["total"] * 0.3
    return {
        **scores,
        "slop_penalty": slop_result["total"],
        "slop_details": slop_result,
        "overall_score": max(1.0, round(overall, 2)),
        "raw_evaluation": "Evaluation unavailable (API error)",
    }


def quick_slop_check(text: str) -> dict:
    """Quick slop check without full evaluation."""
    detector = SlopDetector(text)
    return detector.detect()


if __name__ == "__main__":
    # Test slop detection
    test_text = """
    The ancient temple stood on a mysterious realm, its powerful magic emanating from
    an eternal source. Sarah delve deep into the cryptic texts, utilizing her knowledge
    to unlock the secrets. "It's worth noting that," she said, her eyes widening,
    "the prophecy mentions this exact scenario."

    The journey ahead would be transformative, a game-changer for the legendary heroes.
    John's heart pounded as he approached the sacred chamber. "Not just any weapon,"
    he thought, "but the ultimate power."
    """

    result = quick_slop_check(test_text)
    print("Slop detection test:")
    for k, v in result.items():
        print(f"  {k}: {v}")
