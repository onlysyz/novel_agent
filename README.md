# NovelForge

> Autonomous novel writing powered by dual-agent AI system.

Transform a rough concept into a complete novel — 80,000+ words with consistent world-building, character arcs, and prose style.

## Features

- **5-Layer Architecture**: Voice → World → Characters → Outline → Chapters
- **Dual-Agent System**: Writer Agent drafts, Review Agent evaluates & revises
- **9-Dimension Scoring**: Voice adherence, beat coverage, character voice, foreshadowing, prose quality, continuity, canon compliance, lore integration, engagement
- **Mechanical Slop Detection**: Regex-based banned word/phrasing detection
- **Opus Deep Review**: Claude Opus reviews as literary critic + professor of fiction
- **Reader Panel**: 4 simulated personas evaluate each chapter
- **Adversarial Editing**: Aggressive cuts to force creativity
- **Multi-Format Export**: PDF (LaTeX), ePub, TXT, Audiobook

## Architecture

```
seed.txt
    │
    ▼
┌─────────────────────────────────────────┐
│           Foundation Phase              │
│  world.md → characters.md → outline.md  │
│  canon.md → voice.md                    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           Drafting Phase                │
│  Sequential chapter writing             │
│  9-dimension scoring + retry logic      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           Review System                 │
│  Mechanical checks                      │
│  Reader panel (4 personas)              │
│  Opus deep review                       │
│  Adversarial editing                     │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           Export                         │
│  PDF · ePub · Audiobook                 │
└─────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/nousresearch/autonovel.git
cd novelforge

# Install dependencies
uv sync

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage

```bash
# Start from scratch with a new concept
echo "A retired assassin is forced back into service when her daughter is kidnapped." > seed.txt
python run_pipeline.py --from-scratch

# Resume from last state
python run_pipeline.py

# Run only foundation phase
python run_pipeline.py --phase foundation

# Limit revision cycles
python run_pipeline.py --max-cycles 4
```

## Project Structure

```
novelforge/
├── run_pipeline.py       # Main orchestrator
├── draft_chapter.py      # Chapter drafting
├── evaluate.py           # 9-dimension scoring
├── review.py             # Opus deep review
├── gen_world.py          # World bible generation
├── gen_characters.py     # Character generation
├── gen_outline.py        # Outline + foreshadowing
├── voice_fingerprint.py  # Style analysis
├── anti_patterns.md      # Writing rules
└── .env.example          # API configuration
```

## Writing Rules (Anti-Patterns)

The AI follows strict writing rules to avoid generic AI prose:

- **Show, don't tell** — Trust the gesture, the silence
- **No triadic listing** — Two items are stronger than three
- **Limited passive negatives** — Max 1 "He did not..." per chapter
- **Real dialogue** — False starts, interruptions, imperfect lines
- **70%+ scene time** — Summary only for time compression
- **Sentence variety** — 1-2 sentence paragraphs for impact, 6+ for building
- **Surprising moments** — 1 unexpected beat per chapter

See [ANTI-PATTERNS.md](ANTI-PATTERNS.md) for full rules.

## Scoring System

Each chapter is evaluated on 9 dimensions (score 1-10):

| Dimension | Description |
|-----------|-------------|
| Voice Adherence | Prose matches defined writing style |
| Beat Coverage | All outline beats dramatized |
| Character Voice | Dialogue is distinct and authentic |
| Plants Seeded | Foreshadowing placed naturally |
| Prose Quality | Sentence variety, specificity |
| Continuity | Flow from previous chapter |
| Canon Compliance | Facts match world bible |
| Lore Integration | World does work in scenes |
| Engagement | Page-turn tension |

Median AI-generated chapter scores **6**. A 7 requires something a generic draft wouldn't do.

## License

MIT
