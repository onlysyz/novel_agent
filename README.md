# NovelForge

[![Tauri](https://img.shields.io/badge/Tauri-2.x-FFC107?style=flat-square&logo=tauri)](https://tauri.app)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://python.org)
[![MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)]()

> Autonomous novel writing desktop application powered by dual-agent AI.

A desktop app that transforms a rough concept into a complete 80,000+ word novel — with consistent world-building, character arcs, layered outlining, iterative drafting, and multi-format export.

## Features

### Dual-Agent System

The pipeline runs two distinct AI agents in a continuous feedback loop:

- **Writer Agent** — Uses Claude Sonnet to draft chapters following the voice, outline, and world bible
- **Review Agent** — Uses Claude Opus to evaluate each draft and request specific revisions

The Writer drafts, the Reviewer critiques, the Writer revises. This loop repeats until the Reviewer approves or revision cycles are exhausted.

### 9-Dimension Scoring

Every chapter is evaluated on nine dimensions, each scored 1–10:

| Dimension | What it measures |
|-----------|-----------------|
| Voice Adherence | Prose matches the defined writing style |
| Beat Coverage | All outline beats are dramatized, not summarized |
| Character Voice | Dialogue is distinct; characters sound like themselves |
| Plants Seeded | Foreshadowing is planted naturally, not bolted on |
| Prose Quality | Sentence variety, specificity, show-don't-tell |
| Continuity | Logical and emotional flow from previous chapter |
| Canon Compliance | Facts match the world bible (1 major violation caps score at 6) |
| Lore Integration | World details do real work in scenes, not just set dressing |
| Engagement | Page-turn tension, unexpected moments, momentum |

A median AI-generated chapter scores **6**. A 7 requires something a generic draft wouldn't produce. Chapters scoring below 6 are retried up to 5 times.

### Autonomous Pipeline Phases

The pipeline runs in three ordered phases, each building on the last:

**1. Foundation Phase**

Generates all planning documents before a single chapter is written:

```
seed.txt → world.md → characters.md → outline.md → canon.md → voice.md
```

Each document iterates with feedback until it meets a minimum quality threshold (typically 7.0–7.5). The canon document cross-references all facts for consistency.

**2. Drafting Phase**

Chapters are written sequentially, one at a time. Each chapter:

- Assembles context from all five foundation layers
- Writes ~3,200 words following the outline beats
- Scores on all nine dimensions
- Retries automatically if score < 6.0

**3. Review Phase**

Multi-cycle review after drafting completes:

- **Mechanical checks** — Regex-based anti-pattern scanner (triadic listing, passive negatives, cataloging interiority, etc.)
- **Reader Panel** — 4 simulated personas (genre fan, literary reader, continuity hunter, emotional reader) vote on issues
- **Opus Deep Review** — Claude Opus reviews as a literary critic + professor of fiction
- **Adversarial Editing** — Aggressive cuts (2,000–3,000 words removed) to force creative density

The review loop continues until stopping conditions are met: rating ≥ 4.5 with zero major issues, or ≤ 2 total items identified.

### Mechanical Slop Detection

Built-in regex detection flags generic AI prose patterns:

- Tier 1 banned words (`delve`, `utilize`, `paradigm`) — up to 4pt penalty
- Tier 2 suspicious word clusters — up to 2pt penalty
- Tier 3 filler phrases — up to 2pt penalty
- AI tells (`eyes widened`, `heart pounded`) — up to 2pt penalty
- Em dash density > 15/1,000 words — up to 1pt penalty
- Low sentence variation (CV < 0.3) — 1pt penalty

### Multi-Format Export

Once drafting and review are complete, export to:

- **PDF** — LaTeX typesetting, print-ready
- **ePub** — Reflowable ebook format
- **TXT** — Plain text manuscript

## Requirements

- **Python**: 3.11+
- **Node.js**: 18+ (for frontend build)
- **Rust**: 1.70+ (for Tauri)
- **Anthropic API Key**: [Get one here](https://anthropic.com)
- **macOS**: For DMG bundling (or Linux with adaptations)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/onlysyz/novel_agent.git
cd novel_agent
```

### 2. Set up Python environment

```bash
uv sync
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

### 3. Set up frontend

```bash
cd frontend
npm install
```

### 4. Build and run

```bash
# Build the Tauri app
npm run tauri:build

# Or run in development mode
npm run tauri dev
```

### 5. Build DMG (macOS)

```bash
# Requires create-dmg: brew install create-dmg
npm run clean-dmg && npm run tauri:build && npm run bundle-dmg
```

## Usage

### Desktop App

Open the app and either:

- **New Project** — Enter a seed concept or paste an existing `seed.txt`
- **Open Project** — Point to an existing `.novelforge/` directory

The app runs through all phases automatically, or you can jump to a specific phase.

### CLI Mode

```bash
# Run from scratch with a new concept
echo "A retired assassin is forced back into service when her daughter is kidnapped." > seed.txt
python run_pipeline.py --from-scratch

# Resume from last state
python run_pipeline.py

# Run only foundation phase
python run_pipeline.py --phase foundation

# Resume drafting at a specific chapter
python run_pipeline.py --phase drafting --chapter 5
```

## Architecture

The application is built in three layers: a **Tauri desktop shell** (Rust + React) that wraps a **Python pipeline**, composed of four sub-systems.

### Frontend — Tauri (Rust + React)

The desktop UI is a Tauri 2 application. The Rust backend (`frontend/src-tauri/src/lib.rs`) handles all native operations via IPC commands:

- **File operations** — Read/write seed.txt, chapters, foundation documents, state.json
- **Pipeline control** — Start or resume the writing pipeline from any phase
- **Export** — List available exports, open in default app, download as binary
- **Project management** — Create new projects, open existing ones

The React frontend (`frontend/src/`) renders the project dashboard, chapter list, and export browser. All commands pass a `cwd` parameter so the Rust layer resolves paths relative to the project root.

### Backend — Python Pipeline (`src/`)

| Sub-system | Location | Purpose |
|------------|----------|---------|
| **Foundation** | `src/foundation/` | Generates world, characters, outline, canon, voice documents |
| **Drafting** | `src/drafting/` | Writes chapters sequentially; scores each on 9 dimensions |
| **Review** | `src/review/` | Opus deep review, reader panel, adversarial editing |
| **Export** | `src/export/` | Converts manuscript to PDF, ePub, TXT |

The orchestrator is `run_pipeline.py` — it drives all phases, persists state, and exposes a `--phase` flag for incremental runs.

### State Management

Pipeline state lives in `.novelforge/state.json`:

```json
{
  "phase": "drafting",
  "current_chapter": 5,
  "chapter_scores": { "ch_01": 7.2, "ch_02": 6.8 },
  "revision_cycles": 2,
  "last_updated": "2026-04-19T10:30:00Z"
}
```

Each phase writes its progress so the pipeline can be resumed mid-run. The Tauri frontend reads this file to display the project dashboard.

### Export System

```
chapters/ch_*.md → manuscript.md → [export/]
                                     ├── manuscript.tex → PDF (LaTeX)
                                     ├── *.epub         → ePub
                                     └── *.txt          → Plain text
```

The Rust layer exposes three export commands: `list_exports` (enumerate), `open_export_file` (open in default app), and `get_export_file` (base64-encoded download).

### Pipeline Flow

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
│  Sequential chapter writing              │
│  9-dimension scoring + retry logic      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           Review System                 │
│  Mechanical checks                       │
│  Reader panel (4 personas)               │
│  Opus deep review                        │
│  Adversarial editing                    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           Export                         │
│  PDF · ePub · TXT                        │
└─────────────────────────────────────────┘
```

See [design.md](design.md) for the full architecture specification.

## Project Structure

```
novel_agent/
├── run_pipeline.py           # CLI orchestrator
├── src/
│   ├── foundation/            # world, characters, outline, canon, voice generation
│   ├── drafting/              # chapter drafting + 9-dimension scoring
│   ├── review/                # opus review, reader panel, adversarial editing
│   └── export/                # LaTeX, ePub, TXT export
├── frontend/
│   ├── src/                  # React UI components
│   └── src-tauri/             # Rust backend (Tauri commands)
├── scripts/                  # Build helper scripts
├── chapters/                  # Generated chapter files
├── .novelforge/              # Pipeline state directory
├── design.md                 # Full architecture doc
├── ANTI-PATTERNS.md          # Writing rules
└── CLAUDE.md                 # Developer guide
```

## Writing Rules

The AI follows strict anti-pattern rules to avoid generic prose:

- **Show, don't tell** — Trust the gesture, the silence
- **No triadic listing** — Two items are stronger than three
- **Limited passive negatives** — Max 1 "He did not..." per chapter
- **Real dialogue** — False starts, interruptions, imperfect lines
- **70%+ scene time** — Summary only for time compression
- **Sentence variety** — 1-2 sentence paragraphs for impact, 6+ for building
- **Surprising moments** — 1 unexpected beat per chapter

See [ANTI-PATTERNS.md](ANTI-PATTERNS.md) for full rules.

## Scoring System

Each chapter is evaluated on 9 dimensions (score 1–10):

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

## Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required) |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Writing model |
| `CLAUDE_OPUS_MODEL` | `opus-4-5-20251114` | Review model |
| `TARGET_WORD_COUNT` | `80000` | Novel word count target |
| `CHAPTER_TARGET` | `22` | Number of chapters |
| `MIN_FOUNDATION_SCORE` | `7.0` | Min score to accept foundation docs |
| `MIN_CHAPTER_SCORE` | `6.0` | Min score before chapter retry |
| `MAX_FOUNDATION_ITERATIONS` | `15` | Max retries per foundation doc |
| `MAX_REVIEW_CYCLES` | `3` | Max revision cycles |

## Contributing

Contributions welcome. Please read [CLAUDE.md](CLAUDE.md) for developer guidelines and the 5-layer architecture conventions.

## License

MIT
