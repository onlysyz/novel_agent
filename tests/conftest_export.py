"""Export module fixtures — imported into conftest.py by pytest."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


# ─── Sample text fixtures ──────────────────────────────────────────────────────

SAMPLE_MANUSCRIPT_MD = """# The Hidden Kingdom

## Chapter 1: The Awakening

The ancient door groaned as Sarah pushed it open. Dust motes swirled in the pale morning light that filtered through the shattered stained glass.

She stepped into the cathedral ruins, her boots crunching on broken stone. The vaulted ceiling above had collapsed decades ago, letting in a cascade of morning mist.

## Chapter 2: The Discovery

Marcus arrived at the ruins just as the sun broke through the clouds. He found Sarah standing before an altar covered in strange symbols.

"We need to decode these," she said, holding up her mother's journal.
"""

SAMPLE_CHAPTER_TEXT = """# Chapter 1: The Gathering Storm

Sarah stood in the ruined cathedral, her boots crunching on broken glass. The vaulted ceiling above had collapsed decades ago, letting in the pale morning light.

She reached into her coat pocket and pulled out the broken amulet. It was still warm.

## Scene Beats

The scene unfolded as she examined her mother's last gift.

## World Building

The ruins spoke of a time when this place had been sacred ground.
"""


# ─── Mocked NOVEL_DIR filesystem ───────────────────────────────────────────────

def build_mock_novedir(tmp_path: Path) -> dict[str, Path]:
    """Create a minimal novel directory structure and return path mappings."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()

    (chapters_dir / "ch_01.md").write_text(
        "# Chapter One\n\n"
        "This is the first chapter. It has some content.\n\n"
        "And a second paragraph.\n"
    )
    (chapters_dir / "ch_02.md").write_text(
        "# Chapter Two\n\n"
        "The second chapter continues the story.\n\n"
        "It also has multiple paragraphs.\n"
    )

    (tmp_path / "seed.txt").write_text(
        "A mysterious fantasy novel about a hidden kingdom."
    )
    (tmp_path / "outline.md").write_text(
        "# The Hidden Kingdom\n\nA mysterious fantasy novel."
    )
    (tmp_path / "manuscript.md").write_text(SAMPLE_MANUSCRIPT_MD)

    return {
        "chapters_dir": chapters_dir,
        "seed": tmp_path / "seed.txt",
        "outline": tmp_path / "outline.md",
        "manuscript": tmp_path / "manuscript.md",
    }


# ─── Fixtures ─────────────────────────────────────────────────────────────────

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
    """Create a minimal manuscript.md file for TXT export tests."""
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(SAMPLE_MANUSCRIPT_MD)
    return manuscript


@pytest.fixture
def mock_novedir_export(tmp_path):
    """Create a minimal novel directory structure for export tests.

    Returns a dict with Path objects for key files.
    """
    return build_mock_novedir(tmp_path)


@pytest.fixture
def mock_state_json(tmp_path):
    """Create a minimal state.json for export tests."""
    import json
    state = {
        "phase": "drafting",
        "chapter_count": 2,
        "target_word_count": 50000,
        "current_chapter": 3,
        "outline": {
            "title": "The Hidden Kingdom",
            "chapters": [
                {"number": 1, "title": "The Awakening", "word_count": 3200},
                {"number": 2, "title": "The Discovery", "word_count": 3500},
            ],
        },
        "voice": {
            "style": "Literary and precise prose style.",
            "rules": ["Avoid telling instead of showing."],
        },
        "world": {
            "name": "The Hidden Kingdom",
            "magic_system": "Remnants of ancient magic linger in artifacts.",
        },
        "characters": [
            {"name": "Sarah", "role": "protagonist"},
            {"name": "Marcus", "role": "guide"},
        ],
    }
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state, indent=2))
    return state_file
