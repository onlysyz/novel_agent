"""Reader Panel Evaluation System.

Four simulated reader personas evaluate each chapter:
1. The Genre Fan - Checks genre conventions and expectations
2. The Literary Reader - Evaluates prose craft and technique
3. The Continuity Hunter - Flags plot holes and timeline issues
4. The Emotional Reader - Validates character arcs and emotional beats

Each persona provides specific feedback that's then parsed for consensus.
"""

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client

NOVEL_DIR = Path(".")


# Reader Persona definitions
READER_PERSONAS = {
    "genre_fan": {
        "name": "The Genre Fan",
        "description": "You've read hundreds of fantasy/thriller/romance novels. You know the tropes, the conventions, the reader expectations. You want the genre promises to be fulfilled.",
        "concerns": [
            "Tropes executed well or subverted meaningfully",
            "Genre conventions respected or intentionally broken",
            "Reader expectations met or surprised",
            "Satisfying genre beats",
            "World-building that honors the genre tradition",
        ],
    },
    "literary_reader": {
        "name": "The Literary Reader",
        "description": "You read literary fiction for the craft. You appreciate beautiful prose, distinct voices, and narrative technique. You notice when sentences sing and when they fall flat.",
        "concerns": [
            "Prose rhythm and sentence variety",
            "Distinct character voices",
            "Show don't tell violations",
            "Sensory detail and imagery",
            "Narrative technique and POV craft",
        ],
    },
    "continuity_hunter": {
        "name": "The Continuity Hunter",
        "description": "You read mysteries and thrillers. You track details obsessively - who said what, when did that happen, does this contradict something earlier? You catch the small errors that break immersion.",
        "concerns": [
            "Timeline consistency",
            "Character knowledge consistency",
            "Plot logic holes",
            "Fact contradictions with earlier chapters",
            "Setup/payoff tracking",
        ],
    },
    "emotional_reader": {
        "name": "The Emotional Reader",
        "description": "You read for the feels. Character arcs, emotional stakes, meaningful relationships. You want to care about characters and feel something as you read.",
        "concerns": [
            "Character arc satisfaction",
            "Emotional stakes clarity",
            "Relationship development",
            "Meaningful character moments",
            "Investment in outcomes",
        ],
    },
}


def generate_persona_review(
    chapter_text: str,
    context: dict,
    persona_key: str,
    chapter_num: int,
) -> dict:
    """Generate a review from a specific reader persona."""
    client = get_client()

    persona = READER_PERSONAS[persona_key]
    brief = context.get("chapter_brief", {})
    world = context.get("world", "")
    characters = context.get("characters", "")

    system_prompt = f"""You are {persona['name']}.

{persona['description']}

You will review this chapter as YOUR persona. Be specific, opinionated, and honest.
Reference actual passages from the chapter when making points."""

    user_prompt = f"""## YOUR PERSONA: {persona['name']}
{persona['description']}

## WHAT YOU CHECK
{chr(10).join(f"- {c}" for c in persona['concerns'])}

## CHAPTER TO REVIEW
{chapter_text[:8000]}

## CHAPTER CONTEXT
Title: {brief.get('title', 'Unknown')}
POV: {brief.get('pov', 'Unknown')}
Genre: {brief.get('beat', 'Unknown')}

## WORLD CONTEXT
{world[:1500] if world else 'No world context'}

## CHARACTER CONTEXT
{characters[:1500] if characters else 'No character context'}

## YOUR TASK

Write your review as {persona['name']}. Address these specific concerns:

1. What WORKS in this chapter for your persona type?
2. What DOESN'T WORK?
3. What SPECIFIC PASSAGE exemplifies the issue?
4. What would you suggest to fix it?

Be direct. Reference passages. Don't be wishy-washy."""

    try:
        response = client.generate(system_prompt, user_prompt, max_tokens=4096)
    except Exception as e:
        print(f"  [{persona['name']}] API error: {e}")
        return {
            "persona": persona_key,
            "name": persona["name"],
            "rating": 3.0,
            "issues": [],
            "raw_review": "",
            "error": str(e),
        }

    # Parse a simple rating from the response
    rating = _parse_persona_rating(response, persona_key)

    # Extract key issues mentioned
    issues = _extract_issues(response)

    return {
        "persona": persona_key,
        "name": persona["name"],
        "rating": rating,
        "issues": issues,
        "raw_review": response,
    }


def _parse_persona_rating(text: str, persona_key: str) -> float:
    """Parse a rating from the persona's review text."""
    patterns = [
        r"rating[:\s]*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*(?:out of)?\s*(?:/|\s*of\s*)\s*(?:5|10)",
        r"★+\s*(\d+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = float(match.group(1))
            if rating > 5:
                rating = rating / 2
            return rating

    # Default based on persona type
    defaults = {
        "genre_fan": 3.5,
        "literary_reader": 3.0,
        "continuity_hunter": 3.5,
        "emotional_reader": 3.5,
    }
    return defaults.get(persona_key, 3.0)


def _extract_issues(text: str) -> list[str]:
    """Extract issue descriptions from review text."""
    issues = []

    # Look for quoted passages (indicates specific criticism)
    quotes = re.findall(r'"([^"]+)"', text)
    for quote in quotes[:3]:  # Take first 3 quoted passages
        if len(quote) > 20 and len(quote) < 200:
            issues.append(f'"{quote[:100]}..."')

    # Look for "doesn't work" patterns
    patterns = [
        r"(?:doesn't|does not|isn't|are not)\s+work[^.]*",
        r"problem with[^.]*",
        r"issue with[^.]*",
        r"failed to[^.]*",
        r"weak[^.]*",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:2]:
            issues.append(match.strip()[:150])

    return issues[:5]  # Limit to 5 issues


def run_reader_panel(
    chapter_text: str,
    context: dict,
    chapter_num: int,
) -> dict:
    """
    Run all four reader personas on a chapter.

    Args:
        chapter_text: The chapter prose
        context: Full context package
        chapter_num: Chapter number

    Returns:
        dict with all persona reviews and consensus issues
    """
    print(f"\n[Reader Panel] Chapter {chapter_num}")
    print("=" * 50)

    results = []
    consensus_issues = []
    all_issues = []

    for persona_key in READER_PERSONAS:
        persona = READER_PERSONAS[persona_key]
        print(f"\n[{persona['name']}]")

        result = generate_persona_review(chapter_text, context, persona_key, chapter_num)
        results.append(result)

        print(f"  Rating: {result['rating']}/5")
        if result.get("issues"):
            print(f"  Issues found: {len(result['issues'])}")

        all_issues.extend(result.get("issues", []))

    # Find consensus issues (mentioned by multiple personas)
    issue_counts = {}
    for issue in all_issues:
        issue_lower = issue.lower()[:50]
        issue_counts[issue_lower] = issue_counts.get(issue_lower, 0) + 1

    consensus_issues = [
        issue for issue, count in issue_counts.items()
        if count >= 2  # Mentioned by 2+ personas
    ]

    # Aggregate ratings
    ratings = [r["rating"] for r in results if not r.get("error")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 3.0

    print("\n" + "=" * 50)
    print("[Reader Panel Summary]")
    print(f"Average Rating: {avg_rating:.2f}/5")
    print(f"Consensus Issues: {len(consensus_issues)}")
    if consensus_issues:
        print("Issues mentioned by 2+ readers:")
        for issue in consensus_issues[:5]:
            print(f"  - {issue[:100]}...")

    return {
        "chapter_num": chapter_num,
        "persona_reviews": results,
        "average_rating": avg_rating,
        "consensus_issues": consensus_issues,
        "all_issues": all_issues,
    }


def parse_consensus(panel_result: dict) -> list[str]:
    """Parse actionable items from consensus issues."""
    # Convert consensus issues to suggested fixes
    consensus = panel_result.get("consensus_issues", [])

    # This would ideally use an LLM to generate specific fix suggestions
    # For now, return the consensus issues as-is
    return consensus


if __name__ == "__main__":
    # Test
    sample = """
    Sarah walked through the forest. The trees were ancient, their branches
    reaching toward the sky like grasping hands. She could feel the magic
    of this place, the weight of centuries pressing down on her.

    "We should keep moving," Marcus said. His eyes scanned the shadows.
    He didn't trust this place, didn't trust the feeling in his gut.

    "Wait," Sarah said. "I hear something."

    They froze. In the distance, a sound - footsteps? Animals? Something else?

    Sarah's heart pounded. She knew they shouldn't be here.
    The prophecy had warned them, but she'd ignored it. Now they would
    pay the price. Or would they?

    "Let's go," she decided. They moved deeper into the forest.
    """

    context = {
        "chapter_brief": {
            "title": "The Forest",
            "pov": "Sarah",
            "beat": "Fun and Games",
        },
        "world": "A fantasy world with magic and prophecy.",
        "characters": "Sarah - protagonist. Marcus - companion.",
    }

    result = run_reader_panel(sample, context, 5)
    print(f"\nFinal Summary: {result['average_rating']:.2f}/5")
