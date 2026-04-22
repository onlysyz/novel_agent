"""Shared constants for novel writing pipeline."""

from pathlib import Path

# Project root directory
NOVEL_DIR = Path(".")

# Default scoring thresholds
DEFAULT_MIN_SCORE = 7.0
DEFAULT_MAX_ITERATIONS = 15

# Chapter targets
TARGET_WORDS_PER_CHAPTER = 3200
MIN_CHAPTER_WORDS = 2500
MAX_CHAPTER_WORDS = 8000

# Foundation generator defaults per type
FOUNDATION_DEFAULTS = {
    "world": {"min_score": 7.0, "max_iterations": 15},
    "characters": {"min_score": 7.0, "max_iterations": 15},
    "outline": {"min_score": 7.5, "max_iterations": 15},
    "canon": {"min_score": 7.0, "max_iterations": 10},
    "voice": {"min_score": 7.0, "max_iterations": 10},
}


def get_foundation_config(doc_type: str) -> dict:
    """Get min_score and max_iterations for a foundation document type."""
    return FOUNDATION_DEFAULTS.get(doc_type, {"min_score": DEFAULT_MIN_SCORE, "max_iterations": DEFAULT_MAX_ITERATIONS})


__all__ = [
    "NOVEL_DIR",
    "DEFAULT_MIN_SCORE",
    "DEFAULT_MAX_ITERATIONS",
    "TARGET_WORDS_PER_CHAPTER",
    "MIN_CHAPTER_WORDS",
    "MAX_CHAPTER_WORDS",
    "FOUNDATION_DEFAULTS",
    "get_foundation_config",
]