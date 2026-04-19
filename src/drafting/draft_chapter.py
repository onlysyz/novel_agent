"""Chapter Drafting Module.

Assembles context and generates prose for individual chapters.
Handles continuity with previous chapters and adherence to outline beats.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common.api import get_client

DOTNOVEL = Path(".novelforge")
NOVEL_DIR = Path(".")

# Chapter word count targets
TARGET_WORDS_PER_CHAPTER = int(os.getenv("TARGET_WORDS_PER_CHAPTER", "3200"))
MIN_CHAPTER_WORDS = int(os.getenv("MIN_CHAPTER_WORDS", "2500"))
MAX_CHAPTER_WORDS = int(os.getenv("MAX_CHAPTER_WORDS", "4500"))

# Writing rules to inject into every chapter prompt
WRITING_RULES = """
## MANDATORY WRITING RULES

You must follow ALL of these rules:

1. **POV**: Stay in the designated POV character's head. No head-hopping.
2. **Show, Don't Tell**: Trust the gesture, the silence, the action. Cut explanations.
3. **Sentence Variety**: Mix 1-2 sentence paragraphs (impact) with 6+ sentence paragraphs (building).
4. **No Triadic Listing**: "X. Y. Z." is banned. Combine two items or skip listing.
5. **Real Dialogue**: Include false starts, interruptions, awkward silences. Characters say wrong things.
6. **Sensory Detail**: Ground scenes in specific physical sensations.
7. **No Over-Polished Dialogue**: Characters don't speak in epigrams. They stumble, repeat, trail off.
8. **Beat Integration**: Every outline beat must be DRAMATIZED, not summarized.
9. **Foreshadow Seeds**: Naturally plant foreshadowing elements listed in the chapter brief.
10. **Continuation**: Begin by picking up seamlessly from where the previous chapter ended.
11. **Scene-Summary Ratio**: 70%+ in-scene. Summary only for time compression.
12. **No "The way X did Y"**: Limit similes to 2 per chapter maximum.
13. **Active Alternatives**: Avoid "He did not..." constructions. Max 1 per chapter.
14. **No "Eyes widened" / "Heart pounded"**: These are AI tells. Use specific physical details instead.
15. **Em dash density**: Maximum 15 em dashes per 1000 words.
16. **Paragraph openings**: Vary what starts paragraphs. Don't start with "However", "Furthermore", "Moreover".
17. **Earned Emotion**: Tension comes from scene work, not narrator assertions.
18. **Character Voice**: Each character must sound DISTINCT. Remove dialogue tags and see if you can still tell who is speaking.
19. **Chapter Ending**: End on a specific structural move (not the same as previous chapter).
20. **Predictable Arc Subversion**: Include 1 surprising moment per chapter where a character says/does the wrong thing.
21. **Chapter Length**: Target 3000-4000 words.
22. **No "It's worth noting that"**: Avoid filler phrases.
23. **No "I'm not saying X. I'm saying Y"**: Avoid this rhetorical formula.
24. **Authentic Interiority**: Real thoughts are messy. Don't list thoughts as topics. Use fragments.
"""


def extract_chapter_brief(outline: str, chapter_num: int) -> dict:
    """Extract chapter-specific beats from the outline.

    Args:
        outline: Full outline text
        chapter_num: Chapter number to extract (1-indexed)

    Returns:
        dict with keys: title, pov, location, beat, emotional_arc,
                        try_fail, scene_beats, foreshadow_plants, payoff_payoffs, word_target
    """
    lines = outline.split("\n")

    chapter_info = {
        "title": f"Chapter {chapter_num}",
        "pov": "",
        "location": "",
        "beat": "",
        "position": "",
        "emotional_arc": "",
        "try_fail": "",
        "scene_beats": [],
        "foreshadow_plants": [],
        "payoff_payoffs": [],
        "word_target": TARGET_WORDS_PER_CHAPTER,
    }

    # Simple parsing - look for chapter markers
    in_chapter = False
    current_section = None
    beats_text = []
    foreshadow_text = []
    payoff_text = []

    for line in lines:
        line = line.strip()

        # Detect chapter header
        chapter_patterns = [
            rf"Chapter {chapter_num}[:\s]",
            rf"^{chapter_num}\.\s+",
            rf"## Chapter {chapter_num}",
            rf"### Chapter {chapter_num}",
        ]
        if any(re.match(p, line, re.IGNORECASE) for p in chapter_patterns):
            in_chapter = True
            # Extract title if present
            title_match = re.search(r"Chapter\s+\d+[:\s]+(.+)", line, re.IGNORECASE)
            if title_match:
                chapter_info["title"] = title_match.group(1).strip()
            continue

        if in_chapter:
            # Check for next chapter (end of current)
            if re.match(r"^(## |### |Chapter \d)", line, re.IGNORECASE):
                break

            # KEY:VALUE detection MUST run BEFORE keyword keyword detection
            # to avoid "beat" in "Scene Beats:" being caught by the keyword check
            if line and ":" in line:
                key = line.split(":", 1)[0].strip()
                key_lower = key.lower()
                key_to_section = {
                    "pov": "pov", "point of view": "pov", "perspective": "pov",
                    "location": "location", "setting": "location", "place": "location",
                    "beat": "beat", "save the cat": "beat",
                    "emotional arc": "emotional_arc", "emotional": "emotional_arc",
                    "try-fail cycle": "try_fail", "try-fail": "try_fail", "try fail": "try_fail", "cycle": "try_fail",
                    "scene beats": "scene_beats", "scene": "scene_beats", "beats": "scene_beats", "events": "scene_beats",
                    "foreshadow plants": "foreshadow_plants", "foreshadow": "foreshadow_plants", "plant": "foreshadow_plants", "seed": "foreshadow_plants",
                    "payoffs": "payoff_payoffs", "payoff": "payoff_payoffs", "pay off": "payoff_payoffs",
                    "word target": "word_target", "word": "word_target",
                    "position": "position",
                    "title": "title",
                }
                if key_lower in key_to_section:
                    current_section = key_to_section[key_lower]
                    value = line.split(":", 1)[1].strip()
                    if current_section not in ["scene_beats", "foreshadow_plants", "payoff_payoffs"]:
                        if isinstance(chapter_info.get(current_section), str):
                            chapter_info[current_section] = value
            elif line.startswith("- ") or line.startswith("* "):
                text = line[2:].strip()
                if current_section == "scene_beats":
                    beats_text.append(text)
                elif current_section == "foreshadow_plants":
                    foreshadow_text.append(text)
                elif current_section == "payoff_payoffs":
                    payoff_text.append(text)
            else:
                lower_line = line.lower()
                if any(kw in lower_line for kw in ["pov", "point of view", "perspective"]):
                    current_section = "pov"
                elif any(kw in lower_line for kw in ["location", "setting", "place"]):
                    current_section = "location"
                elif any(kw in lower_line for kw in ["beat", "save the cat"]):
                    current_section = "beat"
                elif any(kw in lower_line for kw in ["emotional", "arc"]):
                    current_section = "emotional_arc"
                elif any(kw in lower_line for kw in ["try-fail", "try fail", "cycle"]):
                    current_section = "try_fail"
                elif any(kw in lower_line for kw in ["scene", "beats", "events"]):
                    current_section = "scene_beats"
                elif any(kw in lower_line for kw in ["foreshadow", "plant", "seed"]):
                    current_section = "foreshadow_plants"
                elif any(kw in lower_line for kw in ["payoff", "pay off"]):
                    current_section = "payoff_payoffs"
                elif any(kw in lower_line for kw in ["word", "target"]):
                    current_section = "word_target"

    chapter_info["scene_beats"] = beats_text
    chapter_info["foreshadow_plants"] = foreshadow_text
    chapter_info["payoff_payoffs"] = payoff_text

    return chapter_info


def extract_next_chapter_opener(outline: str, chapter_num: int) -> str:
    """Extract the opening lines/beats of the next chapter for continuity."""
    brief = extract_chapter_brief(outline, chapter_num + 1)
    if brief["scene_beats"]:
        return "Next chapter opens with: " + brief["scene_beats"][0]
    return ""


def get_previous_chapter_ending(chapters_dir: Path, chapter_num: int) -> str:
    """Get the last ~2000 characters of the previous chapter for continuity."""
    if chapter_num <= 1:
        return ""

    prev_file = chapters_dir / f"ch_{chapter_num-1:02d}.md"
    if not prev_file.exists():
        return ""

    text = prev_file.read_text()
    # Get last ~2000 chars
    if len(text) > 2000:
        return "...\n\n" + text[-2000:]
    return text


def build_context_package(chapter_num: int) -> dict:
    """Assemble the full context package for chapter writing.

    Returns a dict with all context texts needed for chapter generation.
    """
    # Read all layer files
    voice = (NOVEL_DIR / "voice.md").read_text() if (NOVEL_DIR / "voice.md").exists() else ""
    world = (NOVEL_DIR / "world.md").read_text() if (NOVEL_DIR / "world.md").exists() else ""
    characters = (NOVEL_DIR / "characters.md").read_text() if (NOVEL_DIR / "characters.md").exists() else ""
    outline = (NOVEL_DIR / "outline.md").read_text() if (NOVEL_DIR / "outline.md").exists() else ""
    canon = (NOVEL_DIR / "canon.md").read_text() if (NOVEL_DIR / "canon.md").exists() else ""
    anti_patterns = (NOVEL_DIR / "ANTI-PATTERNS.md").read_text() if (NOVEL_DIR / "ANTI-PATTERNS.md").exists() else ""

    # Extract chapter-specific info from outline
    chapter_brief = extract_chapter_brief(outline, chapter_num)
    next_chapter_hint = extract_next_chapter_opener(outline, chapter_num)

    # Get previous chapter ending
    chapters_dir = NOVEL_DIR / "chapters"
    prev_ending = get_previous_chapter_ending(chapters_dir, chapter_num)

    return {
        "voice": voice,
        "world": world,
        "characters": characters,
        "outline": outline,
        "canon": canon,
        "anti_patterns": anti_patterns,
        "chapter_brief": chapter_brief,
        "next_chapter_hint": next_chapter_hint,
        "prev_ending": prev_ending,
    }


def build_chapter_prompt(ctx: dict, chapter_num: int) -> tuple[str, str]:
    """Build the system and user prompts for chapter generation."""
    brief = ctx["chapter_brief"]

    system = f"""You are a novel writer. You write literary fiction with depth, authenticity, and craft.

You understand:
- Show, don't tell - trust the image, the gesture, the silence
- Dan Harmon's story structure and Save the Cat beats
- Character-driven storytelling with authentic dialogue
- The difference between scene and summary
- How to plant foreshadowing naturally

You are writing Chapter {chapter_num} of the novel.

Follow ALL writing rules below. These are not suggestions - they are mandatory."""

    user = f"""## VOICE REFERENCE
{ctx['voice'] or 'No voice guide provided - write in a clear, literary style.'}

## WRITING RULES
{WRITING_RULES}

## ANTI-PATTERNS TO AVOID
{ctx['anti_patterns'] or 'See writing rules above.'}

## WORLD CONTEXT (relevant sections)
{ctx['world'][:4000] if ctx['world'] else 'No world context available.'}

## CHARACTER CONTEXT (relevant profiles)
{ctx['characters'][:4000] if ctx['characters'] else 'No character context available.'}

## CANONICAL FACTS (MUST NOT VIOLATE)
{ctx['canon'][:3000] if ctx['canon'] else 'No canonical facts provided.'}

## CHAPTER {chapter_num} BRIEF

**Title**: {brief['title']}
**POV Character**: {brief['pov'] or 'Not specified'}
**Location**: {brief['location'] or 'Not specified'}
**Beat Type**: {brief['beat'] or 'Not specified'}
**Position in Novel**: {brief['position'] or 'Not specified'}
**Emotional Arc**: {brief['emotional_arc'] or 'Not specified'}
**Try-Fail Cycle**: {brief['try_fail'] or 'Not specified'}
**Word Count Target**: {brief['word_target']}

**Scene Beats to Cover**:
{chr(10).join(f"- {beat}" for beat in brief['scene_beats']) if brief['scene_beats'] else '- No specific beats listed'}

**Foreshadowing to Plant**:
{chr(10).join(f"- {p}" for p in brief['foreshadow_plants']) if brief['foreshadow_plants'] else '- No specific foreshadowing required'}

**Payoffs to Deliver** (from earlier plants):
{chr(10).join(f"- {p}" for p in brief['payoff_payoffs']) if brief['payoff_payoffs'] else '- No payoffs required this chapter'}

{f'''

## PREVIOUS CHAPTER ENDING (continue from here):
{ctx["prev_ending"]}

''' if ctx["prev_ending"] else ''}

{f'''

## NEXT CHAPTER OPENER (hint for transition):
{ctx["next_chapter_hint"]}

''' if ctx["next_chapter_hint"] else ''}

## YOUR TASK

Write Chapter {chapter_num} ({brief['title']}) following the above brief.

IMPORTANT:
- Target {brief['word_target']} words (range: {MIN_CHAPTER_WORDS}-{MAX_CHAPTER_WORDS})
- Begin by continuing naturally from the previous chapter
- Hit every scene beat listed above
- Plant foreshadowing naturally - don't make it obvious
- Deliver any payoffs listed
- Maintain the voice style from the reference
- Do NOT violate any canonical facts
- End on a specific structural note that sets up the next chapter

Write the full chapter now. Output ONLY the chapter prose, nothing else."""

    return system, user


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def draft_chapter(
    chapter_num: int,
    context: dict = None,
    max_retries: int = 5,
    min_score: float = 6.0,
) -> dict:
    """
    Generate a single chapter with retry logic.

    Args:
        chapter_num: Chapter number to write (1-indexed)
        context: Pre-assembled context package (generated if not provided)
        max_retries: Maximum generation attempts
        min_score: Minimum acceptable score

    Returns:
        dict with keys: text, word_count, chapter_num, score, attempts
    """
    client = get_client()

    if context is None:
        context = build_context_package(chapter_num)

    chapters_dir = NOVEL_DIR / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    output_path = chapters_dir / f"ch_{chapter_num:02d}.md"

    brief = context["chapter_brief"]
    target = brief.get("word_target", TARGET_WORDS_PER_CHAPTER)

    print(f"\n[Chapter {chapter_num}] {brief['title']}")
    print(f"  POV: {brief['pov']}, Beat: {brief['beat']}")
    print(f"  Target: ~{target} words")
    print()

    # Import evaluate lazily to avoid circular imports
    sys.path.insert(0, str(NOVEL_DIR))
    from src.drafting.evaluate import evaluate_chapter

    best_result = None
    best_score = 0.0

    for attempt in range(1, max_retries + 1):
        print(f"[Chapter {chapter_num}] Attempt {attempt}/{max_retries}")

        system, user = build_chapter_prompt(context, chapter_num)

        try:
            text = client.generate(system, user, max_tokens=8192, temperature=0.5)
        except Exception as e:
            print(f"  API error: {e}")
            if attempt == max_retries:
                raise
            continue

        word_count = count_words(text)
        print(f"  Generated {word_count} words")

        # Check word count bounds
        if word_count < MIN_CHAPTER_WORDS:
            print(f"  WARNING: Below minimum ({word_count} < {MIN_CHAPTER_WORDS})")
        elif word_count > MAX_CHAPTER_WORDS:
            print(f"  WARNING: Above maximum ({word_count} > {MAX_CHAPTER_WORDS})")

        # Evaluate the chapter
        print(f"  Evaluating...")
        eval_result = evaluate_chapter(text, context)

        print(f"  Overall Score: {eval_result['overall_score']:.1f}")
        print(f"    Voice: {eval_result['voice_adherence']:.1f}, ")
        print(f"    Beats: {eval_result['beat_coverage']:.1f}, ")
        print(f"    Character: {eval_result['character_voice']:.1f}")
        print(f"    Slop Penalty: -{eval_result['slop_penalty']:.1f}")

        if eval_result["overall_score"] > best_score:
            best_score = eval_result["overall_score"]
            best_result = {
                "text": text,
                "word_count": word_count,
                "chapter_num": chapter_num,
                "score": eval_result["overall_score"],
                "attempts": attempt,
                "evaluation": eval_result,
            }

        if eval_result["overall_score"] >= min_score:
            print(f"  ✓ Score {eval_result['overall_score']:.1f} >= {min_score} - ACCEPTED")
            break
        else:
            print(f"  ✗ Score {eval_result['overall_score']:.1f} < {min_score} - RETRY")
            if attempt < max_retries:
                print("  Refining context for next attempt...")
    else:
        print(f"  Max retries reached. Best score: {best_score:.1f}")

    # Save the best result
    if best_result:
        output_path.write_text(best_result["text"])
        print(f"\n  Saved to: {output_path}")

    return best_result or {
        "text": "",
        "word_count": 0,
        "chapter_num": chapter_num,
        "score": 0.0,
        "attempts": max_retries,
        "evaluation": {},
    }


def draft_all_chapters() -> list[dict]:
    """Draft all chapters sequentially."""
    # Determine chapter count from outline or env
    outline_path = NOVEL_DIR / "outline.md"
    if outline_path.exists():
        outline = outline_path.read_text()
        # Count chapters in outline
        chapter_count = len(re.findall(r"(?:^|\n)(?:Chapter|## Chapter|# Chapter)\s+\d+", outline, re.IGNORECASE))
        if chapter_count == 0:
            chapter_count = int(os.getenv("CHAPTER_TARGET", "22"))
    else:
        chapter_count = int(os.getenv("CHAPTER_TARGET", "22"))

    print(f"Drafting {chapter_count} chapters...")

    chapters_dir = NOVEL_DIR / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing chapters (resume capability)
    existing = sorted(chapters_dir.glob("ch_*.md"))
    start_chapter = len(existing) + 1

    if start_chapter > 1:
        print(f"Resuming from chapter {start_chapter} ({len(existing)} chapters already exist)")

    results = []

    for chapter_num in range(start_chapter, chapter_count + 1):
        context = build_context_package(chapter_num)
        result = draft_chapter(chapter_num, context)
        results.append(result)

        # Save progress after each chapter
        state_path = DOTNOVEL / "state.json"
        if state_path.exists():
            import json
            state = json.loads(state_path.read_text())
            state["current_chapter"] = chapter_num
            state["chapter_scores"] = state.get("chapter_scores", {})
            state["chapter_scores"][f"ch_{chapter_num:02d}"] = result["score"]
            state_path.write_text(json.dumps(state, indent=2))

    return results


if __name__ == "__main__":
    chapter_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = draft_chapter(chapter_num)
    print(f"\nFinal: {result['word_count']} words, score {result['score']:.1f}")
