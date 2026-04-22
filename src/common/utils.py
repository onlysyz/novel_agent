"""Shared utilities for novel writing pipeline."""

from pathlib import Path
from typing import List, Tuple, Optional

CHAPTERS_DIR = Path("chapters")
CHAPTER_PREFIX = "ch"
CHAPTER_SUFFIX = ".md"
REVISE_SUFFIX = "_revised"


def list_chapters(novel_dir: Path) -> List[Tuple[int, str, Path]]:
    """List all chapter files in the novel directory.

    Returns:
        List of (chapter_num, title, path) tuples sorted by chapter number.
    """
    chapters_dir = novel_dir / CHAPTERS_DIR
    if not chapters_dir.exists():
        return []

    chapters = []
    for f in sorted(chapters_dir.glob(f"{CHAPTER_PREFIX}_*{CHAPTER_SUFFIX}")):
        # Skip revised chapters
        if REVISE_SUFFIX in f.stem:
            continue
        # Extract chapter number from filename like "ch_01.md"
        stem = f.stem  # e.g., "ch_01" or "ch_01_revised"
        parts = stem.split("_")
        if len(parts) >= 2 and parts[0] == CHAPTER_PREFIX:
            try:
                num = int(parts[1])
                title = _extract_title_from_chapter(f)
                chapters.append((num, title, f))
            except ValueError:
                continue
    return sorted(chapters, key=lambda x: x[0])


def _extract_title_from_chapter(path: Path) -> str:
    """Extract title from chapter file's first H1 heading."""
    try:
        content = path.read_text(encoding="utf-8")
        import re
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return path.stem


def get_chapter_path(novel_dir: Path, chapter_num: int) -> Path:
    """Get the path for a specific chapter file."""
    return novel_dir / CHAPTERS_DIR / f"{CHAPTER_PREFIX}_{chapter_num:02d}{CHAPTER_SUFFIX}"


def get_latest_chapter_path(novel_dir: Path) -> Optional[Path]:
    """Get the path to the most recently created chapter."""
    chapters = list_chapters(novel_dir)
    if not chapters:
        return None
    return chapters[-1][2]  # Return the path of the last chapter


def load_chapters_simple(novel_dir: Path) -> List[Tuple[int, str, str]]:
    """Load all chapters with content - for export modules.

    Returns:
        List of (chapter_num, title, content) tuples sorted by chapter number.
    """
    chapters_dir = novel_dir / CHAPTERS_DIR
    if not chapters_dir.exists():
        return []

    chapters = []
    for entry in sorted(chapters_dir.glob(f"{CHAPTER_PREFIX}_*{CHAPTER_SUFFIX}")):
        # Skip revised versions for now
        if REVISE_SUFFIX in entry.stem:
            continue

        num_str = entry.stem.replace(f"{CHAPTER_PREFIX}_", "")
        try:
            num = int(num_str)
        except ValueError:
            continue

        content = entry.read_text(encoding="utf-8")

        # Check for revised version
        revised_path = chapters_dir / f"{CHAPTER_PREFIX}_{num:02}{REVISE_SUFFIX}{CHAPTER_SUFFIX}"
        if revised_path.exists():
            content = revised_path.read_text(encoding="utf-8")

        # Extract title from first heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else f"Chapter {num}"

        chapters.append((num, title, content))

    return chapters


__all__ = ["list_chapters", "get_chapter_path", "get_latest_chapter_path", "load_chapters_simple", "CHAPTERS_DIR", "CHAPTER_PREFIX"]