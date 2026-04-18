"""Adversarial Editing System.

Aggressively cuts content to force creativity and prevent padding.
The adversarial editor finds and removes:
- Redundant explanations
- Over-wound prose
- Padding and throat-clearing
- Excessive setup before payoff
- Words that do nothing

This prevents the "AI tendency" to fill space with safe, generic prose.
"""

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client

NOVEL_DIR = Path(".")

# Default cut target (words to remove)
DEFAULT_CUT_TARGET = 500


class AdversarialEditor:
    """Finds and suggests cuts in prose."""

    # Patterns that often indicate padding or redundancy
    CUT_PATTERNS = {
        "explanation_after_emotion": {
            "pattern": r"(He/she felt .+?)\.\s+(?:He/she knew this because|This was because|This meant that|Which meant|And this)",
            "reason": "Explaining emotion after showing it",
            "severity": "medium",
        },
        "repetition_of_previous": {
            "pattern": r"(.{50,})\n\n\1",
            "reason": "Repeated passage",
            "severity": "high",
        },
        "windup_before_action": {
            "pattern": r"(?:He/she (?:took a deep breath|gulped|nodded|swallowed)|A moment passed)\.\s+(?:Then |After that |)(She/He)",
            "reason": "Wind-up before action that delays it",
            "severity": "low",
        },
        "filter_words": {
            "pattern": r"\b(?:He saw that|She heard that|They knew that|It was clear that|Obviously|In fact|Of course|Essentially|Basically)\s+",
            "reason": "Filter words that distance reader from experience",
            "severity": "medium",
        },
        "meta_commentary": {
            "pattern": r"(?:She had to admit|He had to think|It was worth noting|In other words|To put it another way|That is to say)",
            "reason": "Authorial commentary within scene",
            "severity": "medium",
        },
    }

    def __init__(self, text: str):
        self.original_text = text
        self.word_count = len(text.split())
        self.cuts_made = []

    def find_auto_cuts(self) -> list[dict]:
        """Find obvious cuts without LLM."""
        cuts = []

        for name, info in self.CUT_PATTERNS.items():
            matches = re.finditer(info["pattern"], self.original_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                context = match.group(0)[:200]
                cuts.append({
                    "type": name,
                    "match": context,
                    "reason": info["reason"],
                    "severity": info["severity"],
                    "word_count": len(context.split()),
                    "position": match.start(),
                })

        return cuts

    def calculate_cut_target(self, target: int = DEFAULT_CUT_TARGET) -> dict:
        """Calculate how much to cut and where."""
        auto_cuts = self.find_auto_cuts()
        auto_cut_words = sum(c["word_count"] for c in auto_cuts)

        return {
            "target": target,
            "auto_cuts_available": len(auto_cuts),
            "auto_cut_words": auto_cut_words,
            "remaining_to_cut": max(0, target - auto_cut_words),
        }


def generate_adversarial_review(
    chapter_text: str,
    context: dict,
    chapter_num: int,
    cut_target: int = DEFAULT_CUT_TARGET,
) -> dict:
    """
    Generate adversarial edit suggestions for a chapter.

    The adversarial editor's job is to CUT 500+ words that are:
    - Redundant or repetitive
    - Over-explaining
    - Padding with generic prose
    - Throat-clearing before important moments

    Args:
        chapter_text: The chapter prose
        context: Full context package
        chapter_num: Chapter number
        cut_target: Target words to cut

    Returns:
        dict with cut suggestions and revised text
    """
    client = get_client()

    brief = context.get("chapter_brief", {})
    word_count = len(chapter_text.split())

    system_prompt = """You are an ADVERSARIAL EDITOR.

Your job is to make the prose TIGHTER and more POWERFUL by cutting words.
You are not gentle - you find the padding, the throat-clearing, the redundant explanations.

You cut:
- Explanations after emotions (show, then explain = tell)
- Words that repeat what was just shown
- Generic prose that could be about any story
- Setup that delays payoff
- False tension (building without release)
- Filter words that distance reader (he saw that, she heard that, it was clear that)
- Hedging and qualification that weakens prose
- "In that moment" / "At that time" type throat-clearing
- Section breaks that don't earn their space

You do NOT cut:
- Character voice and distinct dialogue
- Sensory details that ground scenes
- Necessary setup for major payoffs
- Emotional beats that are earned
- Foreshadowing that's properly planted

Your edits should make the prose READ like it was written by a confident author, not an AI filling space."""

    user_prompt = f"""## ADVERSARIAL EDITING TASK

Cut {cut_target}+ words from this chapter to make it tighter and more powerful.

## CHAPTER TO EDIT
Title: {brief.get('title', 'Unknown')}
POV: {brief.get('pov', 'Unknown')}
Current Word Count: {word_count}
Target Cut: {cut_target}+ words

---

{chapter_text[:12000]}

---

## YOUR TASK

1. **First, identify specific cuts** by quoting passages and explaining what to cut and why.

2. **Then provide the REVISED chapter** with those cuts applied.
   - Mark cuts with [CUT: ...] at the point of removal
   - Keep ALL other content intact
   - The revised version should read as one continuous narrative

3. **Report your cuts**:
   - Total words cut
   - Specific passages (quoted) and why they were cut
   - The revised chapter text

Format your response as:

## CUTS IDENTIFIED
1. [quoted passage] - [reason for cut] - [word count]
2. [quoted passage] - [reason for cut] - [word count]
...

Total: X words to cut

## REVISED CHAPTER
[Full revised chapter text with [CUT: ...] markers]"""

    try:
        response = client.generate(system_prompt, user_prompt, max_tokens=8192)
    except Exception as e:
        print(f"Adversarial edit API error: {e}")
        return {
            "cuts": [],
            "cuts_total_words": 0,
            "revised_text": chapter_text,
            "error": str(e),
        }

    # Parse response
    cuts = _parse_cuts(response)
    revised_text = _extract_revised_text(response, chapter_text)

    # Also run auto-detection
    editor = AdversarialEditor(chapter_text)
    auto_cuts = editor.find_auto_cuts()

    return {
        "llm_cuts": cuts,
        "llm_cuts_total_words": sum(c.get("word_count", 0) for c in cuts),
        "auto_cuts": auto_cuts,
        "revised_text": revised_text,
        "raw_response": response,
    }


def _parse_cuts(text: str) -> list[dict]:
    """Parse cut suggestions from LLM response."""
    cuts = []

    # Look for numbered list of cuts
    pattern = r"(?:^|\n)\d+[.)]\s+\[([^\]]+)\]\s*-\s*([^-]+)\s*-\s*(\d+)\s*words?"
    matches = re.findall(pattern, text, re.MULTILINE)

    for match in matches:
        cuts.append({
            "passage": match[0].strip(),
            "reason": match[1].strip(),
            "word_count": int(match[2]),
        })

    return cuts


def _extract_revised_text(text: str, fallback: str) -> str:
    """Extract revised chapter text from response."""
    # Look for "## REVISED CHAPTER" or similar marker
    markers = [
        r"## REVISED CHAPTER\s*\n\s*(.+?)(?=\n\n##|\Z)",
        r"REVISED VERSION\s*\n\s*(.+?)(?=\n\n##|\Z)",
        r"\[CUT:",
    ]

    for marker in markers:
        match = re.search(marker, text, re.MULTILINE | re.DOTALL)
        if match:
            result = match.group(1) if len(match.groups()) > 0 else match.group(0)
            # Clean up [CUT: ...] markers
            result = re.sub(r"\[CUT:[^\]]*\]", "", result)
            result = re.sub(r"\n{3,}", "\n\n", result)
            if len(result.split()) > 100:  # Sanity check
                return result.strip()

    return fallback


def apply_adversarial_edits(
    chapter_text: str,
    context: dict,
    chapter_num: int,
    cut_target: int = DEFAULT_CUT_TARGET,
) -> dict:
    """
    Apply adversarial edits to a chapter.

    Args:
        chapter_text: Original chapter text
        context: Context package
        chapter_num: Chapter number
        cut_target: Target words to cut

    Returns:
        dict with original, revised, and cut count
    """
    print(f"\n[Adversarial Edit] Chapter {chapter_num}")
    print(f"  Target cut: {cut_target} words")
    print(f"  Original: {len(chapter_text.split())} words")

    result = generate_adversarial_review(chapter_text, context, chapter_num, cut_target)

    if result.get("error"):
        print(f"  Error: {result['error']}")
        return {
            "original": chapter_text,
            "revised": chapter_text,
            "cuts_total_words": 0,
        }

    print(f"  LLM cuts: {result['llm_cuts_total_words']} words")
    print(f"  Auto-detected cuts: {len(result['auto_cuts'])}")

    revised = result["revised_text"]
    revised_words = len(revised.split())
    original_words = len(chapter_text.split())
    actual_cuts = original_words - revised_words

    print(f"  Actual cuts: {actual_cuts} words")
    print(f"  Revised: {revised_words} words")

    if result.get("llm_cuts"):
        print("\n  Sample cuts:")
        for cut in result["llm_cuts"][:3]:
            print(f"    - \"{cut['passage'][:50]}...\" ({cut['word_count']}w)")
            print(f"      Reason: {cut['reason']}")

    return {
        "original": chapter_text,
        "revised": revised,
        "cuts_total_words": actual_cuts,
        "llm_cuts": result.get("llm_cuts", []),
        "auto_cuts": result.get("auto_cuts", []),
    }


def run_adversarial_loop(
    chapter_text: str,
    context: dict,
    chapter_num: int,
    target_cuts: int = 2000,
    max_iterations: int = 2,
) -> dict:
    """
    Run adversarial editing loop until target cuts are achieved.

    Args:
        chapter_text: Original chapter text
        context: Context package
        chapter_num: Chapter number
        target_cuts: Target total words to cut
        max_iterations: Maximum editing passes

    Returns:
        dict with final revised text and cut summary
    """
    current_text = chapter_text
    total_cuts = 0
    iterations_data = []

    print(f"\n[Adversarial Loop] Chapter {chapter_num}")
    print(f"  Target total cuts: {target_cuts} words")
    print()

    for iteration in range(1, max_iterations + 1):
        print(f"  Iteration {iteration}/{max_iterations}")

        result = apply_adversarial_edits(
            current_text,
            context,
            chapter_num,
            cut_target=target_cuts // max_iterations,
        )

        cuts_this_iteration = result["cuts_total_words"]
        total_cuts += cuts_this_iteration
        current_text = result["revised"]

        iterations_data.append({
            "iteration": iteration,
            "cuts": cuts_this_iteration,
            "total_cuts": total_cuts,
        })

        print(f"    Cumulative cuts: {total_cuts}/{target_cuts}")
        print()

        if total_cuts >= target_cuts:
            print(f"  ✓ Target achieved ({total_cuts} words cut)")
            break

        if iteration < max_iterations and cuts_this_iteration < 100:
            print(f"  → Diminishing returns, stopping early")
            break

    return {
        "final_text": current_text,
        "original_text": chapter_text,
        "total_cuts": total_cuts,
        "target_cuts": target_cuts,
        "iterations": iterations_data,
    }


if __name__ == "__main__":
    # Test
    sample = """
    Sarah stood at the window, looking out at the city below. The rain fell
    in sheets, each drop a small percussion against the glass. She felt
    a sense of melancholy settle over her like a heavy blanket.

    The city stretched out below, its neon lights reflecting in puddles
    like scattered diamonds across the dark streets. She'd lived here
    for ten years now, ever since she'd arrived from the small town
    where she'd grown up. The memories of that place still haunted her.

    "I need to get out," she said to herself, her voice barely a whisper.
    She knew that staying here would only make things worse. The past
    had a way of catching up, no matter how far you ran.

    The door opened behind her. She turned, and there he was - the man
    she'd been avoiding for three years. Marcus. Her former partner.
    The one who'd betrayed her. The one who'd shown her that trust
    was just another word for vulnerability.

    "Sarah," he said, his voice echoing in the silent room. "We need to talk."

    She didn't move. Couldn't move. The weight of his presence filled
    the room like a physical force. She could feel the tension in the
    air, thick enough to cut with a knife. She knew she should say
    something, but the words wouldn't come.

    "I know what you're going to say," she finally replied, her voice
    steady despite the turmoil inside. "But I'm not listening. Not today.
    Not after what you did."

    He took a step closer. She could see the regret in his eyes, the
    pain that mirrored her own. He wanted forgiveness, she knew.
    But forgiveness was not something she could give lightly.
    """

    context = {
        "chapter_brief": {
            "title": "The Return",
            "pov": "Sarah",
        }
    }

    result = run_adversarial_loop(sample, context, 5, target_cuts=300)
    print(f"\nFinal cuts: {result['total_cuts']} words removed")
