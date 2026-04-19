"""Fixtures for export module tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def mock_novedir_export(tmp_path):
    """Create a minimal novel directory structure for export tests."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()

    # Create minimal chapters
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

    # Create seed.txt
    seed_file = tmp_path / "seed.txt"
    seed_file.write_text("A mysterious fantasy novel about a hidden kingdom.")

    # Create outline.md
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
def sample_latex_output():
    """Expected LaTeX output for sample_markdown."""
    return (
        r"\section*{Main Title}"
        "\n"
        "This is a paragraph with \\textbf{bold} and \\textit{italic} text."
        "\n"
        r"\par"
        "\n"
        r"\subsection*{Section Two}"
        "\n"
        "Another paragraph with \\textbf{bold} content."
        "\n"
        r"\par"
        "\n"
        r"\hrulefill"
        "\n"
        r"\subsubsection*{Subsection}"
        "\n"
        "Final paragraph."
        "\n"
        r"\par"
        "\n"
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
