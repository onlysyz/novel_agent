"""Pytest fixtures and shared test utilities for draft_chapter tests."""

import pytest
from pathlib import Path
from unittest.mock import mock_open, patch, MagicMock


# ─── Minimal context fixtures ────────────────────────────────────────────────

MINIMAL_OUTLINE = """
# Novel Outline

## Chapter 1: The Beginning
POV: Sarah
Location: The cathedral ruins
Beat: Setup
Emotional Arc: Determination
Try-Fail Cycle: Sarah attempts to rally survivors but fails

Scene Beats:
- Sarah discovers the broken amulet
- She remembers her mother's last words
- The first survivor appears at the door

Foreshadow Plants:
- The amulet glows faintly when touched

Payoffs:
- None required this chapter

## Chapter 2: The Road West
POV: Marcus
Location: The mountain pass
Beat: Fun and Games

Scene Beats:
- Marcus meets the stranger at the tavern
- He receives the map fragment

## Chapter 3: The Dark Forest
POV: Sarah
Location: The dark forest
Beat: Bad Times

Scene Beats:
- The group enters the forest
- Strange sounds echo through the trees
"""

MINIMAL_CONTEXT = {
    "voice": "Literary and precise prose style.",
    "world": "A realm where magic has faded but remnants linger.",
    "characters": "Sarah: a determined survivor.\nMarcus: a reluctant guide.",
    "outline": MINIMAL_OUTLINE,
    "canon": "The old king ruled for 50 years before the fall.",
    "anti_patterns": "Avoid fake emotion and telling instead of showing.",
    "chapter_brief": {
        "title": "The Beginning",
        "pov": "Sarah",
        "location": "The cathedral ruins",
        "beat": "Setup",
        "position": "",
        "emotional_arc": "Determination",
        "try_fail": "Sarah attempts to rally survivors but fails",
        "scene_beats": [
            "Sarah discovers the broken amulet",
            "She remembers her mother's last words",
            "The first survivor appears at the door",
        ],
        "foreshadow_plants": ["The amulet glows faintly when touched"],
        "payoff_payoffs": ["None required this chapter"],
        "word_target": 3200,
    },
    "next_chapter_hint": "",
    "prev_ending": "",
}


# ─── Chapter content fixtures ──────────────────────────────────────────────────

SAMPLE_CHAPTER_TEXT = """# Chapter 1: The Gathering Storm

Sarah stood in the ruined cathedral, her boots crunching on broken glass. The vaulted ceiling above had collapsed decades ago, letting in the pale morning light.

She reached into her coat pocket and pulled out the broken amulet. It was still warm.

## Scene Beats

The scene unfolded as she examined her mother's last gift.

## World Building

The ruins spoke of a time when this place had been sacred ground.
"""


# ─── Mocked filesystem helpers ────────────────────────────────────────────────

def make_mock_file(path: str, content: str) -> MagicMock:
    """Create a mock for Path(...).read_text() returning content."""
    m = MagicMock()
    m.read_text.return_value = content
    m.exists.return_value = True
    return m


def make_mock_dir(path: str) -> MagicMock:
    """Create a mock for a directory Path that exists."""
    m = MagicMock()
    m.exists.return_value = True
    return m


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_context():
    """Return a minimal valid context dict for build_chapter_prompt."""
    from src.drafting.draft_chapter import extract_chapter_brief
    ctx = MINIMAL_CONTEXT.copy()
    ctx["chapter_brief"] = extract_chapter_brief(MINIMAL_OUTLINE, 1)
    return ctx


@pytest.fixture
def minimal_outline():
    """Return the minimal sample outline text."""
    return MINIMAL_OUTLINE


@pytest.fixture
def sample_chapter_text():
    """Return a sample chapter prose text."""
    return SAMPLE_CHAPTER_TEXT


@pytest.fixture
def mock_novedir_files(tmp_path):
    """Mock NOVEL_DIR to return controlled file contents.

    Returns a dict of relative path -> file content mappings.
    All files are mocked to exist with the given content.
    """
    files = {
        "voice.md": "Literary and precise prose style.",
        "world.md": "A realm where magic has faded but remnants linger.",
        "characters.md": "Sarah: a determined survivor.\nMarcus: a reluctant guide.",
        "outline.md": MINIMAL_OUTLINE,
        "canon.md": "The old king ruled for 50 years before the fall.",
        "ANTI-PATTERNS.md": "Avoid fake emotion and telling instead of showing.",
    }

    def _get_mock(path: Path):
        rel = path.name
        if rel in files:
            m = MagicMock()
            m.read_text.return_value = files[rel]
            m.exists.return_value = True
            return m
        m = MagicMock()
        m.exists.return_value = False
        return m

    return files


@pytest.fixture
def mock_prev_chapter(tmp_path):
    """Create a mock previous chapter file for get_previous_chapter_ending."""
    chapter_content = (
        "Sarah stood in the doorway, her heart pounding. "
        "The night had been long, but morning brought new hope. "
        "She stepped outside into the cold air and looked toward the mountains."
    )
    prev_file = tmp_path / "ch_01.md"
    prev_file.write_text(chapter_content)
    return prev_file


# ─── Export fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_novedir_export(tmp_path):
    """Create a minimal novel directory structure for export tests."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()

    chapter1 = chapters_dir / "ch_01.md"
    chapter1.write_text(
        "# Chapter One\n\n"
        "This is the first chapter. It has some content.\n\n"
        "And a second paragraph.\n"
    )

    chapter2 = chapters_dir / "ch_02.md"
    chapter2.write_text(
        "# Chapter Two\n\n"
        "The second chapter continues the story.\n\n"
        "It also has multiple paragraphs.\n"
    )

    seed_file = tmp_path / "seed.txt"
    seed_file.write_text("A mysterious fantasy novel about a hidden kingdom.")

    outline_file = tmp_path / "outline.md"
    outline_file.write_text("# The Hidden Kingdom\n\nA mysterious fantasy novel.")

    return tmp_path


@pytest.fixture
def sample_markdown():
    """Sample markdown text for conversion tests."""
    return (
        "# Main Title\n\n"
        "This is a paragraph with **bold** and *italic* text.\n\n"
        "## Section Two\n\n"
        "Another paragraph with **bold** content.\n\n"
        "---\n\n"
        "### Subsection\n\n"
        "Final paragraph.\n"
    )


@pytest.fixture
def mock_manuscript_md(tmp_path):
    """Create a minimal manuscript.md for TXT export tests."""
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(
        "# My Novel Title\n\n"
        "## Chapter 1\n\n"
        "This is **bold** and this is *italic*.\n\n"
        "Visit [my site](https://example.com) for more.\n"
    )
    return manuscript
