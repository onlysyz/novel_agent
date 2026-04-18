"""Opus Deep Review System.

Claude Opus reviews chapters as two personas:
1. Literary Critic (newspaper style) - evaluates prose quality
2. Professor of Fiction - provides specific, actionable suggestions

Includes review parsing to extract star ratings, severity, and fix types.
"""

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client

NOVEL_DIR = Path(".")

# Review stopping conditions
STOPPING_STAR_THRESHOLD = 4.5
STOPPING_MAX_MAJOR_ITEMS = 0


class ReviewParser:
    """Parse Opus review responses into structured data."""

    @staticmethod
    def parse_star_rating(text: str) -> float:
        """Extract star rating from review."""
        patterns = [
            r"(\d+\.?\d*)\s*(?:out of)?\s*(?:/|\s*of\s*)\s*(?:5|10)\s*stars?",
            r"rating[:\s]*(\d+\.?\d*)",
            r"stars?[:\s]*(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*★",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rating = float(match.group(1))
                # Normalize to 5-star scale if needed
                if rating > 5:
                    rating = rating / 2
                return rating
        return 3.0  # Default

    @staticmethod
    def parse_items(text: str) -> list[dict]:
        """Extract numbered items/suggestions from review."""
        items = []

        # Pattern: numbered items like "1. ...", "2. ...", etc.
        numbered = re.findall(
            r"(?:^|\n)(\d+)[.)]\s+(.+?)(?=(?:\n\d+[.)])|$)",
            text,
            re.MULTILINE | re.DOTALL
        )

        for num, content in numbered:
            item = {
                "number": int(num),
                "content": content.strip(),
                "severity": "moderate",  # default
                "type": "revision",  # default
                "qualified": False,
            }

            # Classify severity
            content_lower = content.lower()
            if any(w in content_lower for w in ["significant", "major", "primary", "critical", "must fix"]):
                item["severity"] = "major"
            elif any(w in content_lower for w in ["minor", "cosmetic", "small", "optional"]):
                item["severity"] = "minor"
            else:
                item["severity"] = "moderate"

            # Classify type
            if any(w in content_lower for w in ["cut", "trim", "compress", "shorten", "reduce"]):
                item["type"] = "compression"
            elif any(w in content_lower for w in ["expand", "add", "introduce", "include", "more"]):
                item["type"] = "addition"
            elif any(w in content_lower for w in ["repetitive", "pattern", "mechanical"]):
                item["type"] = "mechanical"
            elif any(w in content_lower for w in ["rearrange", "reorder", "restructure"]):
                item["type"] = "structural"
            else:
                item["type"] = "revision"

            # Check if qualified (hedged)
            if any(w in content_lower for w in ["perhaps", "may", "might", "could", "largely", "mostly", "if you want"]):
                item["qualified"] = True

            items.append(item)

        return items

    @staticmethod
    def count_severity(items: list[dict]) -> dict:
        """Count items by severity."""
        counts = {"major": 0, "moderate": 0, "minor": 0}
        for item in items:
            counts[item["severity"]] += 1
        return counts

    @staticmethod
    def should_stop(rating: float, items: list[dict]) -> tuple[bool, str]:
        """Determine if revision loop should stop.

        Stopping conditions:
        - Rating >= 4.5 with zero major items
        - Rating >= 4.0 with >50% qualified items
        - Total items <= 2
        """
        if not items:
            return True, "No issues found"

        severity = ReviewParser.count_severity(items)
        qualified_count = sum(1 for i in items if i["qualified"])
        qualified_ratio = qualified_count / len(items) if items else 1.0

        if rating >= STOPPING_STAR_THRESHOLD and severity["major"] == 0:
            return True, f"High rating ({rating}) with no major issues"

        if rating >= 4.0 and qualified_ratio > 0.5:
            return True, f"High qualified ratio ({qualified_ratio:.0%})"

        if len(items) <= 2:
            return True, f"Only {len(items)} items found"

        return False, f"{len(items)} items ({severity['major']} major, {severity['moderate']} moderate, {severity['minor']} minor)"


def opus_review(chapter_text: str, context: dict, chapter_num: int) -> dict:
    """
    Run Opus deep review on a chapter.

    Args:
        chapter_text: The chapter prose
        context: Full context package
        chapter_num: Chapter number for reference

    Returns:
        dict with rating, items, severity counts, and stop decision
    """
    client = get_client()

    # Build context summary for the review
    brief = context.get("chapter_brief", {})
    voice = context.get("voice", "")
    canon = context.get("canon", "")

    system_prompt = """You are Claude Opus, an AI model with exceptional literary criticism capabilities.

You review chapters in TWO PERSONAS:

**PERSONA 1: Literary Critic (Newspaper Style)**
Write 2-3 paragraphs as if you're a newspaper literary critic reviewing this chapter.
Be direct, evaluative, and specific. Reference particular passages.
Do not pull punches - if something doesn't work, say so clearly.

**PERSONA 2: Professor of Fiction**
Write a detailed editorial providing specific, actionable suggestions.
Format as numbered items (1, 2, 3...) that the author should consider.
Be specific - quote passages, name techniques, suggest concrete alternatives.
You are teaching, not just evaluating.

IMPORTANT INSTRUCTIONS:
- Do NOT feel obligated to find defects - if a passage works, say so
- Quote SPECIFIC passages (use quotation marks) when discussing problems or successes
- Suggest concrete ALTERNATIVES, not vague directions
- Consider: prose rhythm, dialogue authenticity, emotional beats, pacing, character voice"""

    user_prompt = f"""Review Chapter {chapter_num} of a novel-in-progress.

## CHAPTER TO REVIEW
{chapter_text[:10000]}

## CHAPTER CONTEXT
Title: {brief.get('title', 'Unknown')}
POV: {brief.get('pov', 'Unknown')}
Beat Type: {brief.get('beat', 'Unknown')}
Emotional Arc: {brief.get('emotional_arc', 'Unknown')}

## VOICE GUIDE
{voice[:2000] if voice else 'No voice guide provided'}

## CANONICAL FACTS (do not violate)
{canon[:1500] if canon else 'No canonical facts provided'}

## YOUR TASK

First, rate the chapter on a 5-star scale and provide your newspaper critic assessment.

Then, provide numbered suggestions (1, 2, 3...) for improvement.
For each suggestion:
- Quote the specific passage you're referring to
- Explain why it needs work OR why it works well
- Suggest a concrete alternative or technique

Format your response as:

**CRITIC'S RATING**: X/5 stars

**CRITIC'S ASSESSMENT**:
[2-3 paragraphs evaluating the chapter as a literary critic]

**PROFESSOR'S SUGGESTIONS**:
1. [Specific suggestion with quoted passage and concrete advice]
2. [Another suggestion]
3. [Another suggestion]
...

If you find no significant issues, write "No major suggestions" after the assessment."""

    try:
        response = client.generate_with_opus(system_prompt, user_prompt, max_tokens=4096)
    except Exception as e:
        print(f"Opus review API error: {e}")
        return {
            "rating": 3.0,
            "items": [],
            "severity": {"major": 0, "moderate": 0, "minor": 0},
            "should_stop": True,
            "stop_reason": "API error - defaulting to stop",
            "raw_review": "",
        }

    # Parse the response
    parser = ReviewParser()
    rating = parser.parse_star_rating(response)
    items = parser.parse_items(response)
    severity = parser.count_severity(items)
    should_stop, stop_reason = parser.should_stop(rating, items)

    return {
        "rating": rating,
        "items": items,
        "severity": severity,
        "should_stop": should_stop,
        "stop_reason": stop_reason,
        "raw_review": response,
    }


def run_opus_review_loop(
    chapter_text: str,
    context: dict,
    chapter_num: int,
    max_iterations: int = 3,
) -> dict:
    """
    Run the Opus review loop until stopping conditions are met.

    Args:
        chapter_text: The chapter prose
        context: Full context package
        chapter_num: Chapter number
        max_iterations: Maximum revision passes

    Returns:
        dict with final review results and iteration count
    """
    current_text = chapter_text
    results = []

    print(f"\n[Opus Review Loop] Chapter {chapter_num}")
    print(f"  Max iterations: {max_iterations}")
    print()

    for iteration in range(1, max_iterations + 1):
        print(f"  Iteration {iteration}/{max_iterations}")

        # Run review
        review_result = opus_review(current_text, context, chapter_num)
        results.append(review_result)

        print(f"    Rating: {review_result['rating']}/5")
        print(f"    Items: {len(review_result['items'])} ({review_result['severity']['major']} major)")
        print(f"    Should stop: {review_result['should_stop']} ({review_result['stop_reason']})")

        if review_result["should_stop"]:
            print(f"    ✓ Stopping condition met")
            break

        # If not stopping and there are items, could apply revisions
        # For now, just record the review - actual revision would need another agent
        print(f"    → {len(review_result['items'])} items need addressing")
        print()

    return {
        "final_rating": results[-1]["rating"],
        "iterations": len(results),
        "results": results,
        "final_review": results[-1],
    }


if __name__ == "__main__":
    # Test with a sample chapter
    sample_chapter = """
    Sarah stood at the window, watching the rain fall. The city stretched out below,
    neon lights reflecting in puddles like scattered diamonds.

    "I need to get out," she said to herself. Her heart pounded in her chest.

    The door opened behind her. She turned, and there he was - the man she'd been
    avoiding for three years. Marcus. Her former partner. The one who'd betrayed her.

    "Sarah," he said, his voice echoing in the silent room. "We need to talk."

    She didn't move. Couldn't move. The weight of his presence filled the room
    like a physical force.

    "I know what you're going to say," she replied, her voice steady despite
    the turmoil inside. "But I'm not listening."
    """

    context = {
        "chapter_brief": {
            "title": "The Return",
            "pov": "Sarah",
            "beat": "All Is Lost",
            "emotional_arc": "Confrontation with past"
        },
        "voice": "",
        "canon": ""
    }

    result = opus_review(sample_chapter, context, 1)
    print(f"\nRating: {result['rating']}/5")
    print(f"Items: {len(result['items'])}")
    print(f"Should stop: {result['should_stop']}")
