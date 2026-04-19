"""Tests for export modules: typeset, epub_export, cover_art, export."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSanitizeLatex:
    """Tests for src.export.typeset.sanitize_latex()."""

    def test_escapes_backslash(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex(r"path\to\file")
        assert r"\textbackslash{}" in result

    def test_escapes_ampersand(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("Rock & Roll")
        assert r"\&" in result

    def test_escapes_percent(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("100% complete")
        assert r"\%" in result

    def test_escapes_dollar(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("$50")
        assert r"\$" in result

    def test_escapes_hash(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("Section #1")
        assert r"\#" in result

    def test_escapes_underscore(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("word_one")
        assert r"\_" in result

    def test_escapes_braces(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("{text}")
        assert r"\{" in result and r"\}" in result

    def test_escapes_tilde(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("a~b")
        assert r"\textasciitilde{}" in result

    def test_escapes_caret(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("a^b")
        assert r"\textasciicircum{}" in result

    def test_escapes_all_special_chars(self):
        from src.export.typeset import sanitize_latex
        text = r"\%$#_{}&\~^"
        result = sanitize_latex(text)
        # All special chars should be escaped
        assert r"\%" in result
        assert r"\$" in result
        assert r"\#" in result
        assert r"\_" in result
        assert r"\{" in result
        assert r"\}" in result
        assert r"\&" in result
        assert r"\textasciitilde{}" in result
        assert r"\textasciicircum{}" in result

    def test_backslash_first_order_matters(self):
        """Backslash must be escaped before other replacements."""
        from src.export.typeset import sanitize_latex
        result = sanitize_latex(r"a\b")
        # Should escape backslash first, not convert \b to something else
        assert r"\textbackslash{}" in result


class TestConvertMarkdownToLatex:
    """Tests for src.export.typeset.convert_markdown_to_latex()."""

    def test_converts_h1(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("# Title")
        assert r"\section*{Title}" in result

    def test_converts_h2(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("## Section")
        assert r"\subsection*{Section}" in result

    def test_converts_h3(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("### Subsection")
        assert r"\subsubsection*{Subsection}" in result

    def test_converts_bold(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("This is **bold** text")
        assert r"\textbf{bold}" in result

    def test_converts_italic_asterisk(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("This is *italic* text")
        assert r"\textit{italic}" in result

    def test_converts_italic_underscore(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("This is _italic_ text")
        assert r"\textit{italic}" in result

    def test_converts_horizontal_rule_dash(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("---\nparagraph\n---")
        assert r"\hrulefill" in result

    def test_converts_horizontal_rule_star(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("***")
        assert r"\hrulefill" in result

    def test_converts_horizontal_rule_underscore(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("___")
        assert r"\hrulefill" in result

    def test_converts_empty_line_ends_paragraph(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("Para one\n\nPara two")
        assert r"\par" in result

    def test_paragraphs_join_on_same_line(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("Line one\nstill same para")
        # Lines on same "paragraph" (no empty line) are joined with space
        # Note: \par is still added at end of paragraph
        assert "Line one still same para" in result

    def test_converts_paragraph_then_header(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("Some paragraph\n\n## Section")
        assert r"\par" in result
        assert r"\subsection*{Section}" in result

    def test_multiple_paragraphs(self, sample_markdown):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex(sample_markdown)
        assert r"\section*{Main Title}" in result
        assert r"\subsection*{Section Two}" in result
        assert r"\subsubsection*{Subsection}" in result
        assert r"\textbf{bold}" in result

    def test_code_blocks_verbatim(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("```\ncode here\n```")
        assert r"\begin{verbatim}" in result
        assert r"\end{verbatim}" in result


class TestEscapeXml:
    """Tests for src.export.epub_export.escape_xml()."""

    def test_escapes_ampersand(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("Tom & Jerry") == "Tom &amp; Jerry"

    def test_escapes_less_than(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("a < b") == "a &lt; b"

    def test_escapes_greater_than(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("a > b") == "a &gt; b"

    def test_escapes_double_quote(self):
        from src.export.epub_export import escape_xml
        assert escape_xml('say "hello"') == "say &quot;hello&quot;"

    def test_escapes_single_quote(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("it's") == "it&apos;s"

    def test_escapes_all(self):
        from src.export.epub_export import escape_xml
        result = escape_xml('a & b < c > d "e" \'f\'')
        assert "a &amp; b" in result
        assert "&lt; c" in result
        assert "&gt; d" in result
        assert "&quot;e&quot;" in result
        assert "&apos;f&apos;" in result

    def test_preserves_normal_text(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("Hello World") == "Hello World"


class TestConvertMarkdownToXhtml:
    """Tests for src.export.epub_export.convert_markdown_to_xhtml()."""

    def test_converts_h1(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("# Title")
        assert "<h1>Title</h1>" in result

    def test_converts_h2(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("## Section")
        assert "<h2>Section</h2>" in result

    def test_converts_h3(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("### Subsection")
        assert "<h3>Subsection</h3>" in result

    def test_converts_bold(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("**bold**")
        assert "<strong>bold</strong>" in result

    def test_converts_italic_asterisk(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("*italic*")
        assert "<em>italic</em>" in result

    def test_converts_italic_underscore(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("_italic_")
        assert "<em>italic</em>" in result

    def test_converts_horizontal_rule(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("---\npara\n---")
        assert "<hr/>" in result

    def test_paragraph_with_text(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("Hello world")
        assert "<p>Hello world</p>" in result

    def test_multiple_paragraphs(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("Para one\n\nPara two")
        assert "<p>Para one</p>" in result
        assert "<p>Para two</p>" in result

    def test_empty_lines_flush_paragraph(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("Para one\n\n\nPara two")
        assert "<p>Para one</p>" in result
        assert "<p>Para two</p>" in result

    def test_escapes_xml_chars_in_text(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("a & b < c > d")
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result


class TestGenerateUuid:
    """Tests for src.export.epub_export.generate_uuid()."""

    def test_returns_string(self):
        from src.export.epub_export import generate_uuid
        result = generate_uuid()
        assert isinstance(result, str)

    def test_returns_valid_uuid_format(self):
        import re
        from src.export.epub_export import generate_uuid
        result = generate_uuid()
        # UUID format: 8-4-4-4-12 hex chars
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(pattern, result) is not None

    def test_returns_different_uuids(self):
        from src.export.epub_export import generate_uuid
        u1 = generate_uuid()
        u2 = generate_uuid()
        assert u1 != u2


class TestBuildCoverPrompt:
    """Tests for src.export.cover_art.build_cover_prompt()."""

    def test_includes_seed(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("A dragon awakens")
        assert "A dragon awakens" in result

    def test_includes_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("A dragon awakens", style="fantasy")
        assert "fantasy" in result.lower() or "Style:" in result

    def test_fantasy_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("magic", style="fantasy")
        assert "epic fantasy" in result or "fantasy" in result.lower()

    def test_scifi_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("space", style="scifi")
        assert "science fiction" in result.lower() or "futuristic" in result.lower()

    def test_thriller_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("danger", style="thriller")
        assert "thriller" in result.lower() or "dark" in result.lower()

    def test_romance_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("love", style="romance")
        assert "romance" in result.lower() or "elegant" in result.lower()

    def test_mystery_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("clue", style="mystery")
        assert "mystery" in result.lower() or "vintage" in result.lower()

    def test_horror_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("fear", style="horror")
        assert "horror" in result.lower() or "dark" in result.lower()

    def test_literary_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("life", style="literary")
        assert "literary" in result.lower() or "minimal" in result.lower()

    def test_unknown_style_defaults_to_fantasy(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("something", style="unknown")
        fantasy_style = GENRE_STYLES["fantasy"]
        assert fantasy_style.split(",")[0] in result

    def test_includes_requirements(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("test")
        assert "Vertical book cover" in result or "2:3" in result or "aspect ratio" in result.lower()

    def test_includes_no_text_requirement(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("test")
        assert "No text" in result or "no text" in result or "title" in result.lower()

    def test_truncates_long_seed(self):
        from src.export.cover_art import build_cover_prompt
        long_seed = "x" * 1000
        result = build_cover_prompt(long_seed)
        # The seed is embedded in prompt, so total length is what matters
        assert len(result) < 2000


class TestExportManuscriptTxt:
    """Tests for src.export.export.export_manuscript_txt()."""

    def test_export_basic_txt(self, mock_manuscript_md, tmp_path):
        from src.export.export import export_manuscript_txt
        from src.export.export import NOVEL_DIR

        # Point to our temp manuscript
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text") as mock_read:
                mock_read.return_value = "# My Novel\n\n## Chapter 1\n\nThis is **bold** and *italic*.\n\n[Link](https://example.com)"
                with patch.object(Path, "write_text") as mock_write:
                    result = export_manuscript_txt(tmp_path)

    def test_removes_markdown_headers(self, tmp_path):
        from src.export.export import export_manuscript_txt

        with patch.object(Path, "read_text") as mock_read:
            mock_read.return_value = "# Title\n\n## Section\n\ncontent"
            with patch.object(Path, "write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "# Title" not in written
                assert "## Section" not in written

    def test_removes_bold_formatting(self, tmp_path):
        from src.export.export import export_manuscript_txt

        with patch.object(Path, "read_text") as mock_read:
            mock_read.return_value = "This is **bold** text"
            with patch.object(Path, "write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "**bold**" not in written
                assert "bold" in written

    def test_removes_italic_formatting(self, tmp_path):
        from src.export.export import export_manuscript_txt

        with patch.object(Path, "read_text") as mock_read:
            mock_read.return_value = "This is *italic* text"
            with patch.object(Path, "write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "*italic*" not in written
                assert "italic" in written

    def test_removes_links(self, tmp_path):
        from src.export.export import export_manuscript_txt

        with patch.object(Path, "read_text") as mock_read:
            mock_read.return_value = "Visit [my site](https://example.com) now"
            with patch.object(Path, "write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "[my site](https://example.com)" not in written
                assert "my site" in written

    def test_returns_error_when_manuscript_missing(self, tmp_path):
        from src.export.export import export_manuscript_txt

        with patch.object(Path, "exists", return_value=False):
            result = export_manuscript_txt(tmp_path)
            assert "error" in result


class TestExportAll:
    """Tests for src.export.export.export_all()."""

    def test_export_all_returns_dict(self, tmp_path):
        from src.export.export import export_all

        with patch("src.export.export.generate_epub") as mock_epub:
            with patch("src.export.export.generate_latex") as mock_latex:
                with patch("src.export.export.compile_pdf") as mock_pdf:
                    with patch("src.export.export.generate_cover") as mock_cover:
                        with patch("src.export.export.export_manuscript_txt") as mock_txt:
                            with patch("src.export.typeset.get_novel_metadata") as mock_meta:
                                mock_epub.return_value = {"epub_path": "test.epub"}
                                mock_latex.return_value = {"tex_path": "test.tex"}
                                mock_pdf.return_value = {"pdf_path": "test.pdf"}
                                mock_cover.return_value = {"cover_path": "test.png"}
                                mock_txt.return_value = {"txt_path": "test.txt"}
                                mock_meta.return_value = {"title": "Test", "author": "Test"}

                                result = export_all(output_dir=tmp_path)
                                assert isinstance(result, dict)

    def test_respects_formats_list(self, tmp_path):
        from src.export.export import export_all

        with patch("src.export.export.export_manuscript_txt") as mock_txt:
            with patch("src.export.typeset.get_novel_metadata") as mock_meta:
                mock_txt.return_value = {"txt_path": "test.txt"}
                mock_meta.return_value = {"title": "Test", "author": "Test"}

                result = export_all(formats=["txt"], output_dir=tmp_path)

                assert "txt" in result
                assert "epub" not in result
                assert "pdf" not in result

    def test_export_all_without_cover(self, tmp_path):
        from src.export.export import export_all

        with patch("src.export.export.export_manuscript_txt") as mock_txt:
            with patch("src.export.export.generate_epub") as mock_epub:
                with patch("src.export.export.generate_latex") as mock_latex:
                    with patch("src.export.export.compile_pdf") as mock_pdf:
                        with patch("src.export.typeset.get_novel_metadata") as mock_meta:
                            mock_txt.return_value = {"txt_path": "test.txt"}
                            mock_epub.return_value = {"epub_path": "test.epub"}
                            mock_latex.return_value = {"tex_path": "test.tex"}
                            mock_pdf.return_value = {"pdf_path": "test.pdf"}
                            mock_meta.return_value = {"title": "Test", "author": "Test"}

                            result = export_all(formats=["txt", "epub", "pdf"], include_cover=False, output_dir=tmp_path)

                            assert "cover" not in result

    def test_falls_back_to_simple_cover_on_error(self, tmp_path):
        from src.export.export import export_all

        with patch("src.export.export.generate_cover") as mock_cover:
            with patch("src.export.export.generate_simple_cover") as mock_simple:
                with patch("src.export.typeset.get_novel_metadata") as mock_meta:
                    mock_cover.return_value = {"error": "No API key"}
                    mock_simple.return_value = {"cover_path": "simple.png", "simple": True}
                    mock_meta.return_value = {"title": "Test", "author": "Test"}

                    result = export_all(formats=["cover"], output_dir=tmp_path)

                    assert "cover" in result
                    assert "simple" in result["cover"]
