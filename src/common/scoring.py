"""Scoring utilities for evaluating generated content."""

import re
from typing import Optional

from .api import get_client


def score_text(
    text: str,
    dimension: str,
    criteria: str,
    context: Optional[dict] = None,
    model: Optional[str] = None,
) -> float:
    """
    Score generated text on a specific dimension.

    Args:
        text: The generated text to score
        dimension: What dimension to score (e.g., "world_coherence", "character_distinctiveness")
        criteria: Specific criteria for this dimension
        context: Additional context for scoring
        model: Override model to use

    Returns:
        Score from 1.0 to 10.0
    """
    client = get_client(model)

    system_prompt = f"""You are an expert literary critic evaluating {dimension}.

Scoring guidelines:
- 9-10: Among the best in published fiction
- 7-8: Strong, publishable with polish
- 5-6: Functional but needs revision
- 3-4: Significant problems
- 1-2: Not usable

Median AI-generated text scores 6. A 7 requires something a generic draft wouldn't do.
Be fair but demanding. Quote specific passages to support your score."""

    user_prompt = f"""Evaluate the following text on dimension: {dimension}

## Criteria
{criteria}

## Text to Evaluate
{text}

{chr(10).join(f'## {k.title()}{chr(10)}{v}' for k, v in (context or {}).items())}

Provide:
1. Score (1-10) with brief justification
2. 2-3 specific quoted passages that support this score
3. One concrete improvement suggestion
"""
    response = client.generate(system_prompt, user_prompt, max_tokens=1024)

    # Parse score from response
    score_match = re.search(r'(?:score|rating)[:\s]*(\d+\.?\d*)', response, re.IGNORECASE)
    if score_match:
        return float(score_match.group(1))
    return 6.0  # Default to passing score


def score_foundation(
    text: str,
    foundation_type: str,
    min_score: float = 7.0,
) -> dict:
    """
    Score foundation documents (world, characters, outline).

    Args:
        text: The generated text
        foundation_type: One of "world", "characters", "outline"
        min_score: Minimum acceptable score

    Returns:
        dict with "score", "passed", and "feedback" keys
    """
    criteria_map = {
        "world": {
            "dimension": "world_coherence",
            "criteria": """Evaluate:
1. **Internal Consistency**: Do lore elements interconnect logically?
2. **Magic System**: Are rules explicit, with costs and limits?
3. **Specificity**: Does it avoid generic fantasy tropes?
4. **Plot Relevance**: Does the world serve the specific story?
5. **Memorability**: Are there unique, distinctive elements?""",
        },
        "characters": {
            "dimension": "character_distinctiveness",
            "criteria": """Evaluate:
1. **Voice Distinction**: Can characters be identified without dialogue tags?
2. **Psychological Depth**: Do characters have believable wounds and arcs?
3. **Plot Necessity**: Is each character essential to the story?
4. **Relationship Dynamics**: Do relationships create meaningful tension?
5. **Authenticity**: Do characters feel like real people, not archetypes?""",
        },
        "outline": {
            "dimension": "plot_structure",
            "criteria": """Evaluate:
1. **Beat Coverage**: Does it hit all Save the Cat beats?
2. **Foreshadowing Ledger**: Are 15+ threads tracked with proper spacing?
3. **Arc Satisfaction**: Do character arcs resolve meaningfully?
4. **Pacing**: Are tension and release properly distributed?
5. **Mechanical Resolvability**: Can mysteries be solved from clues planted?""",
        },
        "canon": {
            "dimension": "canon_completeness",
            "criteria": """Evaluate:
1. **Fact Precision**: Are facts specific and verifiable?
2. **Coverage**: Are all character, political, timeline, and magic facts included?
3. **Knowledge Boundaries**: Are character knowledge states tracked?
4. **Consistency**: Do facts logically align with each other?
5. **Utility**: Can a writer use this to check violations?""",
        },
        "voice": {
            "dimension": "voice_prescription",
            "criteria": """Evaluate:
1. **Distinctiveness**: Does it capture a unique voice, not generic prose?
2. **Prescriptiveness**: Can a writer AI follow these rules?
3. **Specificity**: Are rules concrete, not vague?
4. **Balance**: Does it guide without constraining creativity?
5. **Authenticity**: Does it reflect genuine authorial voice?""",
        },
    }

    if foundation_type not in criteria_map:
        raise ValueError(f"Unknown foundation type: {foundation_type}")

    info = criteria_map[foundation_type]
    score = score_text(text, info["dimension"], info["criteria"])

    return {
        "score": score,
        "passed": score >= min_score,
        "feedback": f"{foundation_type.title()} scored {score:.1f} (min: {min_score})",
    }


def extract_score(response: str) -> float:
    """Extract a numeric score from a text response."""
    match = re.search(r'(\d+\.?\d*)', response)
    if match:
        return float(match.group(1))
    return 6.0


def iteration_summary(iteration: int, score: float, passed: bool) -> str:
    """Format iteration summary."""
    status = "✓ PASSED" if passed else "✗ FAILED"
    return f"Iteration {iteration}: Score={score:.1f} {status}"
