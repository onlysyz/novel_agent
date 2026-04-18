# NovelForge

Autonomous novel writing desktop application powered by dual-agent system.

## Project Overview

A desktop application that transforms an author's rough concept into a complete novel through automated world-building, character development, outline creation, and iterative writing with AI review.

## Tech Stack

- **Frontend**: Tauri (Rust + React)
- **Backend**: Python 3.11+
- **AI Models**: Anthropic Claude ( Sonnet for writing, Opus for review)
- **Storage**: SQLite + JSON state files
- **Export**: LaTeX (PDF), ePub

## Key Files

- `run_pipeline.py` — Main pipeline orchestrator
- `draft_chapter.py` — Single chapter drafting
- `evaluate.py` — 9-dimension scoring system
- `review.py` — Opus deep review
- `gen_world.py` / `gen_characters.py` / `gen_outline.py` — Foundation generation

## Architecture

See `design.md` for full architecture details.

## Commands

```bash
# Install dependencies
uv sync

# Run the pipeline (from scratch)
python run_pipeline.py --from-scratch

# Resume from last state
python run_pipeline.py

# Run specific phase
python run_pipeline.py --phase foundation
```

## Development

This project follows the 5-layer novel architecture from bottom to top:
- Layer 1: `chapters/ch_NN.md` — Prose
- Layer 2: `outline.md` — Plot beats
- Layer 3: `characters.md` — Character profiles
- Layer 4: `world.md` — World bible
- Layer 5: `voice.md` — Writing style

## Anti-Patterns

See `ANTI-PATTERNS.md` for writing rules the AI must follow.

## Settings

Copy `.env.example` to `.env` and configure:
- `ANTHROPIC_API_KEY` — Anthropic API key
- `CLAUDE_MODEL` — Writing model (default: claude-sonnet-4-20250514)
- `CLAUDE_OPUS_MODEL` — Review model (default: opus-4-5-20251114)
- `TARGET_WORD_COUNT` — Novel target (default: 80000)
- `CHAPTER_TARGET` — Chapter count target (default: 22-26)
