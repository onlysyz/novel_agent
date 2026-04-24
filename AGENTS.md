# NovelForge Agent

Autonomous novel writing system powered by dual-agent architecture.

## Project State

**Novel**: 裂世江湖 (Rift World Martial Arts)
**Language**: Chinese (zh)
**Phase**: Drafting (in progress)
**Target**: 25 chapters, ~80,000 words

### Completed
- Foundation: world, characters, outline, canon, voice (avg score: 8.00)
- 15 chapters drafted (scores 5.79 - 6.46)

### In Progress
- Drafting chapters 16-25 (resumed after fixing chapter_target config from 100 → 25)

## Architecture

Dual-agent system:
- **Writer Agent**: Generates chapter prose (MiniMax-M2.7)
- **Reviewer Agent**: Deep review with 9-dimension scoring (Opus)

3-phase pipeline:
1. Foundation → 2. Drafting → 3. Review → Export

## Key Files

- `run_pipeline.py` — Pipeline orchestrator
- `src/drafting/draft_chapter.py` — Chapter generation
- `src/review/review.py` — Deep review scoring
- `src/generators/gen_outline.py` — Plot beat generation

## Commands

```bash
# Resume drafting
uv run python run_pipeline.py --phase drafting

# Full pipeline
uv run python run_pipeline.py --from-scratch

# Export to PDF/ePub
uv run python run_pipeline.py --phase export
```

## Scoring Dimensions

Voice, Beats, Character, Lore, Tension, Dialogue, Pacing, Description, Theme
+ Slop penalty for AI-sounding text

## Config

`.novelforge/config.json` controls:
- `target_words`: 80000
- `chapter_target`: 25
- `model`: MiniMax-M2.7