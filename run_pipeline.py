#!/usr/bin/env python3
"""
NovelForge Pipeline Orchestrator

Complete pipeline for autonomous novel generation:
1. Foundation Phase - Generate world, characters, outline, canon, voice
2. Drafting Phase - Sequential chapter writing with evaluation
3. Review Phase - Multi-cycle revision with reader panel and Opus review
4. Export Phase - Generate final deliverables (PDF, ePub, TXT)

Features:
- State persistence via state.json
- Git version control (auto-commit after each phase)
- Resume from any phase
- --from-scratch to start fresh

Usage:
    python run_pipeline.py                     # Resume from state
    python run_pipeline.py --from-scratch     # Start fresh
    python run_pipeline.py --phase foundation  # Run specific phase
    python run_pipeline.py --phase drafting --chapter 5  # Resume chapter 5
    python run_pipeline.py --full             # Run all phases end-to-end
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# These are initialized in main() after parsing args
DOTNOVEL = None
NOVEL_DIR = None
STATE_FILE = None
CONFIG_FILE = None
PROGRESS_FILE = None

# Phase order for sequential execution
PHASE_ORDER = ["foundation", "drafting", "review", "export"]


def log_progress(phase: str, message: str, step: str = "running"):
    """Write a progress entry to the progress JSONL file."""
    if PROGRESS_FILE is None:
        return
    entry = {
        "phase": phase,
        "step": step,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        with open(PROGRESS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def load_project_config() -> dict:
    """Load project config from file with fallback to env vars."""
    global CONFIG_FILE
    config = {
        "target_words": os.getenv("TARGET_WORDS", "80000"),
        "chapter_target": os.getenv("CHAPTER_TARGET", "22"),
        "output_dir": os.getenv("OUTPUT_DIR", "."),
    }
    if CONFIG_FILE is None:
        return config
    try:
        file_config = json.loads(CONFIG_FILE.read_text())
        for key in ["target_words", "chapter_target", "output_dir"]:
            if file_config.get(key):
                config[key] = file_config[key]
    except Exception:
        pass
    return config


def init_paths(output_dir: str = "."):
    """Initialize paths based on output directory."""
    global DOTNOVEL, NOVEL_DIR, STATE_FILE, CONFIG_FILE, PROGRESS_FILE
    NOVEL_DIR = Path(output_dir) if output_dir and output_dir != "." else Path.cwd()
    DOTNOVEL = NOVEL_DIR / ".novelforge"
    DOTNOVEL.mkdir(parents=True, exist_ok=True)
    STATE_FILE = DOTNOVEL / "state.json"
    CONFIG_FILE = DOTNOVEL / "config.json"
    PROGRESS_FILE = DOTNOVEL / "progress.jsonl"


# =============================================================================
# Git Version Control
# =============================================================================

def git_commit(message: str) -> bool:
    """Create a git commit with the given message."""
    try:
        # Stage all changes
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"],
            capture_output=True,
        )
        if result.returncode == 0:
            print("  No changes to commit")
            return False

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  Committed: {message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Git commit failed: {e}")
        return False


def git_tag(tag: str) -> bool:
    """Create a git tag."""
    try:
        subprocess.run(["git", "tag", tag], check=True, capture_output=True)
        print(f"  Tagged: {tag}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Git tag failed: {e}")
        return False


def git_branch_name(seed: str) -> str:
    """Generate a branch name from the seed."""
    # Take first 6 words, lowercase, alphanumeric only
    words = re.findall(r"\w+", seed.lower())[:6]
    branch = "novel/" + "-".join(words)
    # Sanitize
    branch = re.sub(r"[^a-z0-9/-]", "", branch)
    return branch[:50]


# =============================================================================
# State Management
# =============================================================================

def load_state() -> dict:
    """Load pipeline state from state.json with all required keys."""
    defaults = {
        "phase": "foundation",
        "started_at": None,
        "completed_phases": [],
        "foundation": {},
        "drafting": {
            "current_chapter": 0,
            "chapter_scores": {},
            "total_words": 0,
            "total_attempts": 0,
        },
        "review": {
            "revision_cycles": 0,
            "chapters_reviewed": [],
        },
        "export": {},
    }
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            loaded = json.load(f)
            # Merge with defaults to ensure all keys exist
            for key, value in defaults.items():
                if key not in loaded:
                    loaded[key] = value
            return loaded
    return defaults


def save_state(state: dict):
    """Save pipeline state to state.json."""
    DOTNOVEL.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_phase_index(phase: str) -> int:
    """Get the index of a phase in the execution order."""
    return PHASE_ORDER.index(phase) if phase in PHASE_ORDER else -1


def is_phase_complete(state: dict, phase: str) -> bool:
    """Check if a phase has been completed."""
    return phase in state.get("completed_phases", [])


def get_next_phase(state: dict) -> Optional[str]:
    """Get the next incomplete phase."""
    for phase in PHASE_ORDER:
        if phase not in state.get("completed_phases", []):
            return phase
    return None


# =============================================================================
# Cleanup
# =============================================================================

def cleanup_for_fresh_start(preserve_git: bool = True):
    """Clean up all generated files for a fresh start."""
    print("\nCleaning up for fresh start...")

    # Files to remove
    files_to_remove = [
        "seed.txt",
        "voice.md",
        "world.md",
        "characters.md",
        "outline.md",
        "canon.md",
        "state.json",
    ]

    # Directories to remove
    dirs_to_remove = [
        "chapters",
        "results",
    ]

    # Remove files
    for f in files_to_remove:
        path = NOVEL_DIR / f
        if path.exists():
            path.unlink()
            print(f"  Removed: {f}")

    # Remove directories
    for d in dirs_to_remove:
        path = NOVEL_DIR / d
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed: {d}/")

    # Remove cache if exists
    cache_dir = DOTNOVEL / ".cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"  Removed: .novelforge/.cache/")


# =============================================================================
# Output Helpers
# =============================================================================

def print_header(text: str):
    """Print a section header."""
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def print_phase_summary(phase: str, duration: float, stats: dict):
    """Print a phase completion summary."""
    print(f"\n{phase.upper()} PHASE COMPLETE ({duration:.1f}s)")
    for key, value in stats.items():
        print(f"  {key}: {value}")


# =============================================================================
# Phase: Foundation
# =============================================================================

def run_foundation(state: dict) -> dict:
    """Generate all planning documents.

    Order: world -> characters -> outline -> canon -> voice
    """
    print_header("FOUNDATION PHASE")

    sys.path.insert(0, str(Path(__file__).parent))
    import src.common.prompts as _prompts
    import src.foundation.gen_world as _gw
    import src.foundation.gen_characters as _gc
    import src.foundation.gen_outline as _go
    import src.foundation.gen_canon as _gca
    import src.foundation.voice_fingerprint as _gv
    # Point every generator at the correct output directory
    for _mod in [_prompts, _gw, _gc, _go, _gca, _gv]:
        _mod.NOVEL_DIR = NOVEL_DIR
    generate_world      = _gw.generate_world
    generate_characters = _gc.generate_characters
    generate_outline    = _go.generate_outline
    generate_canon      = _gca.generate_canon
    generate_voice      = _gv.generate_voice

    # Check for seed
    seed_path = NOVEL_DIR / "seed.txt"
    if not seed_path.exists():
        raise FileNotFoundError(
            "seed.txt not found. Create it with your novel concept.\n"
            "Example: echo 'A retired assassin is forced back into service...' > seed.txt"
        )

    # Read seed content (strip language header if present)
    seed_content = seed_path.read_text().strip()
    if seed_content.startswith("[language:"):
        lines = seed_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("[language:") and i + 1 < len(lines) and not lines[i + 1].strip():
                language = line.split(":", 1)[1].strip().rstrip("]")
                seed = "\n".join(lines[i + 2:]).strip()
                break
        else:
            # No empty line after header, find where content starts
            seed = seed_content
            for line in lines:
                if not line.startswith("[language:") and not line.startswith("#") and line.strip():
                    break
            seed = seed.split(line, 1)[1].strip() if line in seed else seed
    else:
        seed = seed_content

    # Read language from header
    language = "en"
    for line in seed_path.read_text().split("\n"):
        if line.startswith("[language:"):
            language = line.split(":", 1)[1].strip().rstrip("]")
            break

    print(f"Novel concept: {seed[:80]}{'...' if len(seed) > 80 else ''}")
    print(f"Language: {language}")
    print()
    log_progress("foundation", f"Novel concept: {seed[:80]}...", "running")

    results = {}

    # Step 1: World Bible
    print("[1/5] World Bible...")
    log_progress("foundation", "[1/5] World Bible...", "running")
    start = time.time()
    result = generate_world(seed=seed, language=language)
    results["world"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "duration": time.time() - start,
    }
    print(f"  Score: {result['score']:.1f}, Iterations: {result['iterations']}")
    log_progress("foundation", f"  World score: {result['score']:.1f}", "running")

    # Step 2: Character Profiles
    print("[2/5] Character Profiles...")
    log_progress("foundation", "[2/5] Character Profiles...", "running")
    start = time.time()
    world = (NOVEL_DIR / "world.md").read_text()
    result = generate_characters(seed=seed, world=world, language=language)
    results["characters"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "duration": time.time() - start,
    }
    print(f"  Score: {result['score']:.1f}, Iterations: {result['iterations']}")
    log_progress("foundation", f"  Characters score: {result['score']:.1f}", "running")

    # Step 3: Story Outline
    print("[3/5] Story Outline...")
    log_progress("foundation", "[3/5] Story Outline...", "running")
    start = time.time()
    characters = (NOVEL_DIR / "characters.md").read_text()
    result = generate_outline(seed=seed, world=world, characters=characters, language=language)
    results["outline"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "duration": time.time() - start,
    }
    print(f"  Score: {result['score']:.1f}, Iterations: {result['iterations']}")
    log_progress("foundation", f"  Outline score: {result['score']:.1f}", "running")

    # Step 4: Canonical Facts
    print("[4/5] Canonical Facts...")
    log_progress("foundation", "[4/5] Canonical Facts...", "running")
    start = time.time()
    outline = (NOVEL_DIR / "outline.md").read_text()
    result = generate_canon(seed=seed, world=world, characters=characters, outline=outline, language=language)
    results["canon"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "duration": time.time() - start,
    }
    print(f"  Score: {result['score']:.1f}, Iterations: {result['iterations']}")
    log_progress("foundation", f"  Canon score: {result['score']:.1f}", "running")

    # Step 5: Voice Fingerprint
    print("[5/5] Voice Fingerprint...")
    log_progress("foundation", "[5/5] Voice Fingerprint...", "running")
    start = time.time()
    result = generate_voice(seed=seed, language=language)
    results["voice"] = {
        "score": result["score"],
        "iterations": result["iterations"],
        "duration": time.time() - start,
    }
    print(f"  Score: {result['score']:.1f}, Iterations: {result['iterations']}")
    log_progress("foundation", f"  Voice score: {result['score']:.1f}", "running")

    # Calculate total duration
    total_duration = sum(r["duration"] for r in results.values())
    total_score = sum(r["score"] for r in results.values()) / len(results)

    print(f"\nTotal duration: {total_duration:.1f}s")
    print(f"Average score: {total_score:.2f}")
    log_progress("foundation", f"Foundation complete. Avg score: {total_score:.2f}", "complete")

    # Git commit
    print("\n[Git] Committing foundation phase...")
    branch = git_branch_name(seed)
    git_commit(f"Foundation: world, characters, outline, canon, voice (avg score: {total_score:.2f})")

    return results


# =============================================================================
# Phase: Drafting
# =============================================================================

def run_drafting(state: dict) -> dict:
    """Sequential chapter writing."""
    print_header("DRAFTING PHASE")

    sys.path.insert(0, str(Path(__file__).parent))
    import src.drafting.draft_chapter as _dc
    import src.drafting.evaluate as _ev
    _dc.NOVEL_DIR = NOVEL_DIR
    _ev.NOVEL_DIR = NOVEL_DIR
    draft_chapter = _dc.draft_chapter
    build_context_package = _dc.build_context_package

    # Determine chapter count from config
    project_config = load_project_config()
    outline_path = NOVEL_DIR / "outline.md"
    chapter_count = int(project_config.get("chapter_target", "22"))
    if outline_path.exists():
        outline = outline_path.read_text()
        found = len(re.findall(r"(?:^|\n)(?:Chapter|## Chapter|# Chapter)\s+\d+", outline, re.IGNORECASE))
        if found > 0:
            chapter_count = found

    print(f"Target: {chapter_count} chapters")
    print()
    log_progress("drafting", f"Target: {chapter_count} chapters", "running")

    # Check for resume
    chapters_dir = NOVEL_DIR / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    existing = sorted(chapters_dir.glob("ch_*.md"))
    start_chapter = state.get("drafting", {}).get("current_chapter", 0) + 1

    if start_chapter > 1:
        print(f"Resuming from chapter {start_chapter} ({len(existing)} chapters exist)")
    elif existing:
        print(f"Found {len(existing)} existing chapters, will overwrite")

    print()

    # Stats
    total_words = state.get("drafting", {}).get("total_words", 0)
    total_attempts = state.get("drafting", {}).get("total_attempts", 0)
    chapter_scores = state.get("drafting", {}).get("chapter_scores", {})

    # Pre-build context for remaining chapters
    print("Pre-building context packages...")
    context_cache = {}
    for ch in range(start_chapter, chapter_count + 1):
        try:
            context_cache[ch] = build_context_package(ch)
            print(f"  Chapter {ch}: {context_cache[ch]['chapter_brief']['title']}")
        except Exception as e:
            print(f"  Chapter {ch}: Error building context - {e}")

    print()

    # Draft chapters
    chapter_start_time = time.time()

    for chapter_num in range(start_chapter, chapter_count + 1):
        ch_start = time.time()
        print(f"\n[Chapter {chapter_num}/{chapter_count}]")
        log_progress("drafting", f"[Chapter {chapter_num}/{chapter_count}]", "running")

        try:
            context = context_cache.get(chapter_num, build_context_package(chapter_num))
            result = draft_chapter(chapter_num, context)

            chapter_scores[f"ch_{chapter_num:02d}"] = result["score"]
            total_words += result["word_count"]
            total_attempts += result["attempts"]

            # Update state
            state["drafting"]["current_chapter"] = chapter_num
            state["drafting"]["chapter_scores"] = chapter_scores
            state["drafting"]["total_words"] = total_words
            state["drafting"]["total_attempts"] = total_attempts
            save_state(state)

            ch_duration = time.time() - ch_start
            print(f"  {result['word_count']} words, score: {result['score']:.1f}, time: {ch_duration:.1f}s")
            log_progress("drafting", f"  Ch {chapter_num}: {result['word_count']} words, score: {result['score']:.1f}", "running")

        except Exception as e:
            print(f"  ERROR: {e}")
            log_progress("drafting", f"  ERROR: {e}", "error")
            state["drafting"]["current_chapter"] = chapter_num
            save_state(state)
            continue

    # Summary
    total_duration = time.time() - chapter_start_time
    avg_score = sum(chapter_scores.values()) / len(chapter_scores) if chapter_scores else 0

    stats = {
        "chapters": chapter_count,
        "words": total_words,
        "attempts": total_attempts,
        "avg_score": f"{avg_score:.2f}",
        "duration": f"{total_duration:.1f}s",
    }

    print_phase_summary("Drafting", total_duration, stats)
    log_progress("drafting", f"Drafting complete. {total_words} words, avg score: {avg_score:.2f}", "complete")

    # Git commit
    print("\n[Git] Committing chapters...")
    git_commit(f"Drafting: {chapter_count} chapters, {total_words:,} words (avg score: {avg_score:.2f})")

    state["drafting"]["total_duration"] = total_duration
    return stats


# =============================================================================
# Phase: Review
# =============================================================================

def run_review(state: dict) -> dict:
    """Multi-cycle revision with adversarial editing, reader panel, and Opus review."""
    print_header("REVIEW PHASE")

    sys.path.insert(0, str(Path(__file__).parent))
    import src.review.review as _rv
    import src.review.adversarial_edit as _ae
    import src.review.reader_panel as _rp
    import src.drafting.draft_chapter as _dc2
    for _mod in [_rv, _ae, _rp, _dc2]:
        _mod.NOVEL_DIR = NOVEL_DIR
    run_reader_panel      = _rp.run_reader_panel
    run_adversarial_loop  = _ae.run_adversarial_loop
    run_opus_review_loop  = _rv.run_opus_review_loop
    build_context_package = _dc2.build_context_package

    # Get chapters
    chapters_dir = NOVEL_DIR / "chapters"
    chapters = sorted(chapters_dir.glob("ch_*.md"))

    if not chapters:
        print("No chapters found. Run drafting phase first.")
        return {}

    chapter_count = len(chapters)
    print(f"Target: {chapter_count} chapters")
    log_progress("review", f"Target: {chapter_count} chapters", "running")

    max_cycles = int(os.getenv("MAX_REVIEW_CYCLES", "3"))
    print(f"Max revision cycles: {max_cycles}")
    log_progress("review", f"Max revision cycles: {max_cycles}", "running")

    revision_cycles = state.get("review", {}).get("revision_cycles", 0)
    chapters_reviewed = state.get("review", {}).get("chapters_reviewed", [])

    cycle_start_time = time.time()

    for cycle in range(1, max_cycles + 1):
        print(f"\n{'='*60}")
        print(f"REVISION CYCLE {cycle}/{max_cycles}")
        print(f"{'='*60}")
        log_progress("review", f"Revision cycle {cycle}/{max_cycles}", "running")

        cycle_improvements = 0

        for chapter_file in chapters:
            chapter_num = int(chapter_file.stem.split("_")[1])

            # Skip if already reviewed in this cycle (basic dedup)
            review_key = f"{cycle}-{chapter_num}"
            if review_key in chapters_reviewed:
                continue

            print(f"\n--- Chapter {chapter_num:02d} ---")
            log_progress("review", f"--- Chapter {chapter_num:02d} ---", "running")

            chapter_text = chapter_file.read_text()
            context = build_context_package(chapter_num)

            # Step 1: Adversarial Edit
            print(f"  [1/3] Adversarial Edit...")
            edit_result = run_adversarial_loop(
                chapter_text,
                context,
                chapter_num,
                target_cuts=500,
                max_iterations=1,
            )

            if edit_result["total_cuts"] > 200:
                revised_path = chapters_dir / f"ch_{chapter_num:02d}_revised.md"
                revised_path.write_text(edit_result["final_text"])
                chapter_text = edit_result["final_text"]
                cycle_improvements += 1
                print(f"  Cut {edit_result['total_cuts']} words")

            # Step 2: Reader Panel
            print(f"  [2/3] Reader Panel...")
            panel_result = run_reader_panel(chapter_text, context, chapter_num)
            print(f"  Reader rating: {panel_result['average_rating']:.2f}/5")

            # Step 3: Opus Deep Review
            print(f"  [3/3] Opus Deep Review...")
            opus_result = run_opus_review_loop(
                chapter_text,
                context,
                chapter_num,
                max_iterations=2,
            )
            print(f"  Opus rating: {opus_result['final_rating']}/5")
            print(f"  Stop: {opus_result['final_review']['stop_reason']}")

            chapters_reviewed.append(review_key)
            revision_cycles += 1

            state["review"]["revision_cycles"] = revision_cycles
            state["review"]["chapters_reviewed"] = chapters_reviewed
            save_state(state)

        print(f"\nCycle {cycle}: {cycle_improvements} chapters revised")

        if cycle_improvements == 0:
            print("No improvements in this cycle. Stopping.")
            break

    total_duration = time.time() - cycle_start_time

    stats = {
        "revision_cycles": revision_cycles,
        "chapters_reviewed": len(set(ch.split("-")[1] for ch in chapters_reviewed)),
        "duration": f"{total_duration:.1f}s",
    }

    print_phase_summary("Review", total_duration, stats)
    log_progress("review", f"Review complete. {revision_cycles} revision cycles.", "complete")

    # Git commit
    print("\n[Git] Committing review phase...")
    git_commit(f"Review: {revision_cycles} revision passes")

    state["review"]["total_duration"] = total_duration
    return stats


# =============================================================================
# Phase: Export
# =============================================================================

def run_export(state: dict) -> dict:
    """Generate final deliverables."""
    print_header("EXPORT PHASE")

    # Import export module
    sys.path.insert(0, str(Path(__file__).parent))
    import src.export.export as _exp
    import src.export.epub_export as _epub
    import src.export.cover_art as _cover
    import src.export.typeset as _typeset
    for _mod in [_exp, _epub, _cover, _typeset]:
        _mod.NOVEL_DIR = NOVEL_DIR
    export_all = _exp.export_all

    # Check that we have chapters
    chapters_dir = NOVEL_DIR / "chapters"
    chapters = sorted(chapters_dir.glob("ch_*.md"))

    if not chapters:
        print("No chapters found. Run drafting phase first.")
        return {}

    chapter_count = len(chapters)
    print(f"Found {chapter_count} chapters")
    print()
    log_progress("export", f"Found {chapter_count} chapters", "running")

    # Assemble manuscript (basic, always done)
    print("Assembling manuscript...")
    manuscript_parts = []
    total_words = 0

    for chapter_file in chapters:
        content = chapter_file.read_text().strip()
        # Check for revised version
        revised_file = chapter_file.parent / f"{chapter_file.stem}_revised.md"
        if revised_file.exists():
            content = revised_file.read_text().strip()

        chapter_num = int(chapter_file.stem.split("_")[1])
        manuscript_parts.append(f"\n\n# Chapter {chapter_num}\n\n{content}")
        total_words += len(content.split())

    manuscript = "\n".join(manuscript_parts)

    # Save full manuscript
    manuscript_path = NOVEL_DIR / "manuscript.md"
    manuscript_path.write_text(manuscript)
    print(f"  Saved: manuscript.md ({total_words:,} words)")
    log_progress("export", f"  manuscript.md saved ({total_words:,} words)", "running")

    # Build results file
    results_path = DOTNOVEL / "results.tsv"
    results_lines = ["chapter\tscore\twords"]
    for chapter_file in chapters:
        chapter_num = int(chapter_file.stem.split("_")[1])
        score = state.get("drafting", {}).get("chapter_scores", {}).get(f"ch_{chapter_num:02d}", "N/A")
        words = len(chapter_file.read_text().split())
        results_lines.append(f"ch_{chapter_num:02d}\t{score}\t{words}")

    results_path.write_text("\n".join(results_lines))
    print(f"  Saved: results.tsv")

    # Run full export (TXT, ePub, LaTeX/PDF, cover)
    print("\n" + "=" * 50)
    print("Generating additional formats...")
    print("=" * 50)

    export_dir = NOVEL_DIR / "export"
    export_dir.mkdir(exist_ok=True)

    try:
        export_results = export_all(
            formats=["txt", "epub", "cover"],
            output_dir=export_dir,
        )

        # Collect output paths
        output_files = ["manuscript.md", "results.tsv"]
        if "txt" in export_results and "txt_path" in export_results["txt"]:
            output_files.append(f"export/{Path(export_results['txt']['txt_path']).name}")
        if "epub" in export_results and "epub_path" in export_results["epub"]:
            output_files.append(f"export/{Path(export_results['epub']['epub_path']).name}")
        if "cover" in export_results and "cover_path" in export_results["cover"]:
            output_files.append(f"export/{Path(export_results['cover']['cover_path']).name}")

        # Note about PDF (requires pdflatex)
        if "pdf" not in export_results or "error" in export_results.get("pdf", {}):
            print("\nNote: PDF generation requires pdflatex (install MacTeX on macOS)")

    except Exception as e:
        print(f"Export error: {e}")
        output_files = ["manuscript.md", "results.tsv"]

    # Summary
    stats = {
        "chapters": chapter_count,
        "total_words": total_words,
        "files": output_files,
    }

    print_phase_summary("Export", 0, stats)
    log_progress("export", f"Export complete. {total_words:,} words.", "complete")

    # Git commit
    print("\n[Git] Committing export...")
    git_commit(f"Export: manuscript ({total_words:,} words)")

    # Create git tag for this version
    tag_name = f"v{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    git_tag(tag_name)

    state["export"] = {
        "completed_at": datetime.now().isoformat(),
        "total_words": total_words,
        "tag": tag_name,
        "files": output_files,
    }

    return stats


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="NovelForge Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                     Resume from last state
  python run_pipeline.py --from-scratch     Start fresh (WARNING: deletes all progress)
  python run_pipeline.py --phase foundation Run only foundation phase
  python run_pipeline.py --full             Run all phases end-to-end
        """,
    )
    parser.add_argument("--from-scratch", action="store_true",
                        help="Start fresh (deletes all progress)")
    parser.add_argument("--phase", choices=PHASE_ORDER,
                        help="Run specific phase only")
    parser.add_argument("--full", action="store_true",
                        help="Run all phases end-to-end")
    parser.add_argument("--seed", type=str,
                        help="Override seed text")
    parser.add_argument("--chapter", type=int,
                        help="Resume from specific chapter (drafting phase)")
    parser.add_argument("--output-dir", type=str, default=".",
                        help="Output directory for novel files (default: current directory)")

    args = parser.parse_args()

    # Initialize paths based on output directory
    init_paths(args.output_dir)

    # Clear progress file for new run
    if PROGRESS_FILE and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
    log_progress("init", "Pipeline started", "running")

    print(f"Output directory: {NOVEL_DIR}")

    # Handle seed override
    if args.seed:
        seed_path = NOVEL_DIR / "seed.txt"
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        seed_path.write_text(args.seed)
        print(f"Seed written to {seed_path}")

    # Handle fresh start
    if args.from_scratch:
        cleanup_for_fresh_start()
        state = {
            "phase": "foundation",
            "started_at": datetime.now().isoformat(),
            "completed_phases": [],
        }
        save_state(state)
        print("Starting fresh. Use --seed to set concept if not using seed.txt")
    else:
        state = load_state()
        if not state.get("started_at"):
            state["started_at"] = datetime.now().isoformat()
            save_state(state)

    # Handle chapter resume
    if args.chapter:
        state["drafting"] = state.get("drafting", {})
        state["drafting"]["current_chapter"] = args.chapter - 1
        save_state(state)
        print(f"Will resume drafting from chapter {args.chapter}")

    print(f"\nNovelForge Pipeline")
    print(f"Started: {state.get('started_at', 'unknown')}")
    print(f"Completed phases: {state.get('completed_phases', [])}")

    # Determine what to run
    if args.full:
        # Run all phases in order
        phases_to_run = [p for p in PHASE_ORDER if p not in state.get("completed_phases", [])]
    elif args.phase:
        # Run specific phase
        phases_to_run = [args.phase]
    else:
        # Resume from next incomplete phase
        next_phase = get_next_phase(state)
        if next_phase:
            phases_to_run = [next_phase]
        else:
            print("\nAll phases complete! Use --from-scratch to start a new novel.")
            print("Or use --phase export to re-export.")
            phases_to_run = []

    if not phases_to_run:
        print("\nNo phases to run.")
        return

    print(f"Phases to run: {phases_to_run}")

    # Run phases
    for phase in phases_to_run:
        print(f"\n{'#'*60}")
        print(f"# PHASE: {phase.upper()}")
        print(f"{'#'*60}")

        phase_start = time.time()

        if phase == "foundation":
            results = run_foundation(state)
            state["foundation"] = results
            state["completed_phases"].append("foundation")
            state["phase"] = "drafting"

        elif phase == "drafting":
            results = run_drafting(state)
            state["drafting"]["stats"] = results
            state["completed_phases"].append("drafting")
            state["phase"] = "review"

        elif phase == "review":
            results = run_review(state)
            state["review"]["stats"] = results
            state["completed_phases"].append("review")
            state["phase"] = "export"

        elif phase == "export":
            results = run_export(state)
            state["export"] = results
            state["completed_phases"].append("export")
            state["phase"] = "complete"

        phase_duration = time.time() - phase_start
        state[f"{phase}_duration"] = phase_duration

        save_state(state)

        print(f"\n{phase.upper()} completed in {phase_duration:.1f}s")

    # Final summary
    print("\n" + "=" * 60)
    print(" PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Completed: {state.get('completed_phases', [])}")

    if args.full:
        total_time = sum(state.get(f"{p}_duration", 0) for p in PHASE_ORDER)
        print(f"Total time: {total_time:.1f}s")

    print()


if __name__ == "__main__":
    main()
