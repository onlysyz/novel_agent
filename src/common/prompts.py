"""Prompt building utilities for Foundation generators."""

from pathlib import Path
from typing import Optional

# Base directories
DOTNOVEL = Path(".novelforge")
NOVEL_DIR = Path(".")


def read_seed() -> str:
    """Read the seed concept, stripping the language header if present."""
    seed_path = NOVEL_DIR / "seed.txt"
    if not seed_path.exists():
        seed_path = DOTNOVEL / "seed.txt"
    if seed_path.exists():
        content = seed_path.read_text().strip()
        # Strip [language: xx] header if present
        if content.startswith("[language:"):
            lines = content.split("\n")
            # Skip until after the empty line following the header
            for i, line in enumerate(lines):
                if line.startswith("[language:") and i + 1 < len(lines) and not lines[i + 1].strip():
                    return "\n".join(lines[i + 2:]).strip()
            # Fallback: just find where content starts
            for i, line in enumerate(lines):
                if not line.startswith("[language:") and not line.startswith("#") and line.strip():
                    return "\n".join(lines[i:]).strip()
        return content
    return ""


def read_language() -> str:
    """Read the language from the seed.txt header."""
    seed_path = NOVEL_DIR / "seed.txt"
    if not seed_path.exists():
        seed_path = DOTNOVEL / "seed.txt"
    if seed_path.exists():
        for line in seed_path.read_text().split("\n"):
            if line.startswith("[language:"):
                lang = line.split(":", 1)[1].strip().rstrip("]")
                return lang.strip()
    return "en"  # default to English


def read_layer(filename: str) -> str:
    """Read a layer file from the project directory."""
    path = NOVEL_DIR / filename
    if not path.exists():
        path = DOTNOVEL / filename
    if path.exists():
        return path.read_text().strip()
    return ""


def read_anti_patterns() -> str:
    """Read anti-patterns for writing."""
    return read_layer("ANTI-PATTERNS.md")


def read_craft_guide() -> str:
    """Read CRAFT.md if it exists."""
    return read_layer("CRAFT.md")


LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}


def _get_language_instruction(language: str) -> str:
    """Get language instruction for prompts."""
    lang_name = LANGUAGE_NAMES.get(language, "English")
    return f"\n\n## Language\nWrite all content in {lang_name}." if language != "en" else ""


def build_world_prompt(
    seed: str,
    voice: Optional[str] = None,
    craft: Optional[str] = None,
    language: str = "en",
) -> tuple[str, str]:
    """Build system and user prompts for world generation."""
    system = """You are a novel architect specializing in creating immersive, consistent fantasy worlds.

You understand:
- Brandon Sanderson's magic system rules (explicit costs, limits, trade-offs)
- Political intrigue and power dynamics
- Economic systems and their implications
- Cultural development and how it shapes societies
- Hard magic vs soft magic trade-offs

Generate a detailed world bible that serves the specific seed concept.
All lore elements must interconnect - nothing exists in isolation."""

    lang_instruction = _get_language_instruction(language)

    user = f"""Generate a world bible for the following novel concept:

## Seed Concept
{seed}
{lang_instruction}

{f'''## Voice Reference
{voice}''' if voice else ''}

{f'''## Craft Guidelines
{craft}''' if craft else ''}

## Requirements

The world bible must include:

1. **Geography & Climate** - Physical world, regions, key locations
2. **Political Structures** - Governments, factions, power hierarchies
3. **Economic Systems** - Trade, resources, economic pressures
4. **Religion & Culture** - Beliefs, customs, social norms
5. **History** - Only events relevant to the present story
6. **Magic Systems** - HARD rules with explicit costs, limits, and trade-offs
7. **Interconnected Lore** - Each element references and affects others

Target 3000-4000 words. Write with specificity - avoid generic fantasy.
Ground everything in concrete details that make this world unique.

## Anti-Patterns to Avoid
- Generic fantasy tropes without twist
- Magic that solves problems without cost
- Cultures that exist only as set dressing
- History that doesn't connect to present conflicts
"""
    return system, user


def build_characters_prompt(
    seed: str,
    world: str,
    voice: Optional[str] = None,
    language: str = "en",
) -> tuple[str, str]:
    """Build prompts for character generation."""
    system = """You are a character architect specializing in creating distinct, memorable characters.

You understand:
- Character arcs and transformation arcs
- Psychological depth (core wound, lie they believe)
- Distinct dialogue patterns and speech rhythms
- Relationships that create tension and meaning
- How characters serve plot while feeling authentic

Generate character profiles that will drive the specific story forward."""

    lang_instruction = _get_language_instruction(language)

    user = f"""Generate character profiles for the following novel:

## Seed Concept
{seed}
{lang_instruction}

## World Bible
{world}

{f'''## Voice Reference
{voice}''' if voice else ''}

## Requirements

Generate 3-8 major characters. Each profile must include:

1. **Physical Presence** - Age, distinguishing features, how they move/hold themselves
2. **Psychological Profile** - Core wound, lie they believe, what they want vs what they need
3. **Speech Patterns** - Vocabulary level, sentence rhythm, catchphrases, verbal tics
4. **Goals** - Surface goal (what they pursue) and deep goal (what they actually need)
5. **Relationships** - Dynamic with other characters, not static descriptions
6. **Arc Trajectory** - How will they change by story's end
7. **Role in Plot** - Why this character is necessary to this specific story

## Character Voice Principles
- No character should sound like another
- Real people stumble, say wrong things, have awkward silences
- Dialogue should reveal character, not just convey information
- Characters should have distinct observational lenses

## Anti-Patterns to Avoid
- Characters who always say the right thing strategically
- Flat characters who serve only as plot devices
- Dialogue that could be interchanged between characters
- Missing flaws or moments of weakness
"""
    return system, user


def build_outline_prompt(
    seed: str,
    world: str,
    characters: str,
    voice: Optional[str] = None,
    mystery: Optional[str] = None,
    language: str = "en",
) -> tuple[str, str]:
    """Build prompts for outline generation with Save the Cat beats."""
    system = """You are a novel architect familiar with:
- Save the Cat beat sheet
- Brandon Sanderson's plotting principles
- Dan Harmon's Story Circle
- MICE Quotient (Milieu, Idea, Character, Event)

Generate a detailed outline targeting 22-26 chapters (~80,000 words total).
Each chapter should be 3000-4000 words."""

    lang_instruction = _get_language_instruction(language)

    user = f"""Generate a complete story outline for:

## Seed Concept
{seed}
{lang_instruction}

## World Bible
{world}

## Character Profiles
{characters}

{f'''## Voice Reference
{voice}''' if voice else ''}

{f'''## Central Mystery/Conflict
{mystery}''' if mystery else ''}

## Structure Requirements

Organize into FOUR ACTS with specific word count allocations:
- **Act I (0-23%)**: Setup, inciting incident, break into two
- **Act II Part 1 (23-50%)**: Fun & Games, midpoint
- **Act II Part 2 (50-77%)**: Bad guys close in, all is lost
- **Act III (77-100%)**: Final battle, climax, denouement

## Per-Chapter Requirements

For each chapter, provide:
1. **Chapter Number & Title**
2. **POV Character**
3. **Location**
4. **Save the Cat Beat** (e.g., Setup, Fun & Games, Bad Guys Close In)
5. **Position Marker** (% through novel)
6. **Emotional Arc** (what changes for POV character)
7. **Try-Fail Cycle Type** (Yes-And, Yes-But, No-And, No-But)
8. **Scene Beats** (3-5 specific beats, dramatized not summarized)
9. **Foreshadowing Plants** (what to seed for later payoff)
10. **Payoffs** (what earlier plants pay off here)
11. **Character Movement** (how relationships/understanding shift)
12. **Word Count Target**

## Foreshadowing Ledger

Create a table tracking 15+ foreshadowing threads:
| Thread | Plant Chapter | Reinforce | Payoff | Type |
|--------|--------------|-----------|--------|------|
Minimum 3-chapter distance between planting and payoff.

## Mechanical Constraints
- Use Perin's Law: Every mystery must be mechanically resolvable
- Character must appear in person (not via message/effect)
- Include three "quiet" chapters (low tension, character development)
- 60%+ of try-fail cycles should be Yes-But or No-And types
"""
    return system, user


def build_canon_prompt(seed: str, world: str, characters: str, outline: str, language: str = "en") -> tuple[str, str]:
    """Build prompts for canonical facts generation."""
    system = """You are a continuity architect. Your job is to extract HARD FACTS from the generated world, characters, and outline.

These facts will be checked against every chapter. Violations cap chapter scores at 6.
Be exhaustive, specific, and precise. When in doubt, write it down."""

    lang_instruction = _get_language_instruction(language)

    user = f"""Extract all canonical facts from the following documents:

## Seed Concept
{seed}
{lang_instruction}

## World Bible
{world}

## Character Profiles
{characters}

## Story Outline
{outline}

## Requirements

Generate canon.md containing:

1. **Character Facts**
   - Full names, titles, nicknames
   - Birth dates/ages (calculate from timeline)
   - Physical descriptions (key features only)
   - Personality traits that affect plot
   - Knowledge boundaries (what they know vs don't know)

2. **Political Facts**
   - Alliance dates and terms
   - Treaty provisions
   - Faction territories
   - Power hierarchies with precise relationships

3. **Timeline**
   - Major historical events with dates
   - Character-relevant events in their pasts
   - Present-day political situation

4. **Geographic Facts**
   - Distances (relevant to travel time)
   - Climate/weather patterns
   - Strategic locations

5. **Magic Rules**
   - Spell costs (specific, not vague)
   - Limitations and boundaries
   - What happens when exceeded

6. **Knowledge Rules**
   - What each character knows at each point
   - Information asymmetry between characters

Format as a reference document. Be specific enough that a writer could be called out for violations."""
    return system, user


def build_voice_prompt(sample_texts: list[str], seed: str, language: str = "en") -> tuple[str, str]:
    """Build prompts for voice/writing style fingerprint."""
    system = """You are a literary analyst specializing in prose style. Analyze the provided texts and extract the essential voice characteristics that make them distinctive."""

    sample_texts_formatted = "\n\n".join(
        f"--- Sample {i+1} ---\n{text}" for i, text in enumerate(sample_texts)
    )

    lang_instruction = _get_language_instruction(language)

    user = f"""Analyze the following sample texts and create a VOICE FINGERPRINT for the author.

## Seed Concept (what the author wants to write)
{seed}
{lang_instruction}

## Sample Texts
{sample_texts_formatted}

## Extract the Following Voice Characteristics

1. **Sentence Rhythm**
   - Average length and variation
   - Use of fragments vs complex sentences
   - Rhythm patterns (短句冲刺, 长句 builds)

2. **Vocabulary Wells**
   - Words used heavily (favorite adjectives, verbs)
   - Technical/genre-specific vocabulary
   - Words to AVOID (overused in genre)

3. **POV Characteristics**
   - Distance from narrator (close/distant)
   - Internal monologue style
   - Sensory prioritization (what senses are evoked)

4. **Dialogue Style**
   - Fragment vs complete sentences
   - Subtext patterns
   - How much characters reveal vs conceal

5. **Prose Patterns**
   - Favorite constructions
   - Patterns to avoid (generic genre prose)
   - Use of imagery types (metaphor, simile, sensory)

6. **Tone Indicators**
   - Dark/light balance
   - Irony levels
   - Formality register

Format as a prescriptive voice.md that a writer AI should follow.
This should feel like THIS author voice, not generic prose."""
    return system, user
