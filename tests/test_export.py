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
        # Backslash replaced with \textbackslash{}
        assert r"\textbackslash{}" in result
        # Original path segments preserved (no \t = tab, \f = formfeed)
        assert "path" in result
        assert "to" in result
        assert "file" in result

    def test_escapes_ampersand(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("Rock & Roll")
        # & must be escaped as \&
        assert r"\&" in result
        # The & char should not appear unescaped (un-prefixed by \)
        # Check by looking for \& (escaped) vs raw & appearing elsewhere
        assert result.replace(r"\&", "") == "Rock  Roll"

    def test_escapes_percent(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("100% complete")
        assert r"\%" in result
        assert result.replace(r"\%", "") == "100 complete"

    def test_escapes_dollar(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("$50")
        assert r"\$" in result
        assert result.replace(r"\$", "") == "50"

    def test_escapes_hash(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("Section #1")
        assert r"\#" in result
        assert result.replace(r"\#", "") == "Section 1"

    def test_escapes_underscore(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("word_one")
        assert r"\_" in result
        assert result.replace(r"\_", "") == "wordone"

    def test_escapes_open_brace(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("{text}")
        assert r"\{" in result
        assert result.replace(r"\{", "").replace(r"\}", "") == "text"

    def test_escapes_close_brace(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("text}")
        assert r"\}" in result
        assert result.replace(r"\}", "") == "text"

    def test_escapes_tilde(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("a~b")
        assert r"\textasciitilde{}" in result
        assert result.replace(r"\textasciitilde{}", "") == "ab"

    def test_escapes_caret(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("a^b")
        assert r"\textasciicircum{}" in result
        assert result.replace(r"\textasciicircum{}", "") == "ab"

    def test_no_double_escaping_of_braces_in_backslash_replacement(self):
        r"""Braces inside \textbackslash{} must not be re-escaped to \\\{ \\\}."""
        from src.export.typeset import sanitize_latex
        result = sanitize_latex(r"a\b")
        # The replacement string \textbackslash{} has { and } which must NOT become \{ \}
        # Only the literal braces in the input should be escaped
        assert r"\textbackslash{}" in result
        # The braces inside \textbackslash{} should not be escaped as \{
        # If double-escaped we'd see \\{
        assert r"\\\{" not in result

    def test_backslash_with_brace_input(self):
        """A backslash followed by a brace — brace must only be escaped once."""
        from src.export.typeset import sanitize_latex
        result = sanitize_latex(r"\{")
        # \{ is the correct escape for an open brace
        # Not \\\{ (which would be backslash + escaped brace)
        assert r"\{" in result
        assert r"\\\{" not in result

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
        assert r"\textbackslash{}" in result

    def test_multiple_backslashes(self):
        from src.export.typeset import sanitize_latex
        # Three backslash characters in the input
        input_val = "a\\b\\c"
        result = sanitize_latex(input_val)
        # a\b\c has 2 backslashes, each becomes \textbackslash{}
        assert result.count(r"\textbackslash{}") == 2

    def test_mixed_special_chars_no_interference(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex(r"100% @ #1 & $50 _test_ {a} ~b ^c")
        # None of the escapes should interfere with each other
        assert r"\%" in result
        assert r"\@" not in result  # @ is not special
        assert r"\#" in result
        assert r"\$" in result
        assert r"\_" in result
        assert r"\{" in result
        assert r"\}" in result
        assert r"\textasciitilde{}" in result
        assert r"\textasciicircum{}" in result

    def test_idempotent(self):
        """Running sanitize_latex twice should give the same result."""
        from src.export.typeset import sanitize_latex
        original = "Hello World"
        once = sanitize_latex(original)
        twice = sanitize_latex(once)
        assert once == twice

    def test_backslash_with_existing_braces_in_input(self):
        """Input containing both backslash and braces is handled correctly."""
        from src.export.typeset import sanitize_latex
        result = sanitize_latex(r"\text{block}")
        # \text -> \textbackslash{} , {block} -> \{block\}
        assert r"\textbackslash{}" in result
        assert r"\{block\}" in result

    def test_preserves_normal_text(self):
        from src.export.typeset import sanitize_latex
        result = sanitize_latex("Hello World")
        assert result == "Hello World"


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

    def test_empty_text(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("")
        assert result == ""

    def test_plain_text_no_formatting(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("Just some plain text.")
        assert "Just some plain text." in result

    def test_italic_underscore_mid_word(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("This is _really_ important.")
        assert r"\textit{really}" in result

    def test_bold_and_italic_combined(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("***bold italic***")
        assert r"\textbf{" in result
        assert r"\textit{bold italic}" in result

    def test_header_requires_space_after_hash(self):
        """# must be followed by a space to be recognized as a header."""
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("#NoSpaceHere")
        # Without space, it's treated as plain text (no \section)
        assert r"\section*" not in result
        assert "#NoSpaceHere" in result

    def test_multiple_consecutive_headers(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("# Header1\n## Header2\n### Header3")
        assert r"\section*{Header1}" in result
        assert r"\subsection*{Header2}" in result
        assert r"\subsubsection*{Header3}" in result

    def test_paragraph_without_trailing_newline(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("A paragraph without newline")
        assert "A paragraph without newline" in result

    def test_paragraph_mixed_bold_italic(self):
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("This has **bold** and *italic* together.")
        assert r"\textbf{bold}" in result
        assert r"\textit{italic}" in result

    def test_bold_only_supports_double_asterisk(self):
        """Bold only supports **...**, not __...__ (underscore is italic)."""
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("This is __bold__ text")
        # __...__ is not treated as bold — underscores are italic
        assert r"\textbf{bold}" not in result
        # The first _ triggers italic, content includes remaining underscores
        assert r"\textit{" in result

    def test_links_not_converted(self):
        """Markdown links are not converted by this function."""
        from src.export.typeset import convert_markdown_to_latex
        result = convert_markdown_to_latex("See [this](https://example.com)")
        # Links pass through unchanged (this function doesn't handle them)
        assert "[this](https://example.com)" in result


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

    def test_escapes_all_special_chars_together(self):
        from src.export.epub_export import escape_xml
        result = escape_xml('a & b < c > d "e" \'f\'')
        assert "a &amp; b" in result
        assert "&lt; c" in result
        assert "&gt; d" in result
        assert "&quot;e&quot;" in result
        assert "&apos;f&apos;" in result

    def test_escapes_ampersand_exactly(self):
        """Ampersand is escaped to &amp; (not &amp;amp; etc)."""
        from src.export.epub_export import escape_xml
        assert escape_xml("&") == "&amp;"
        assert escape_xml("&&") == "&amp;&amp;"

    def test_escapes_less_than_exactly(self):
        """Less-than is escaped to &lt;."""
        from src.export.epub_export import escape_xml
        assert escape_xml("<") == "&lt;"
        assert escape_xml("<<") == "&lt;&lt;"

    def test_escapes_greater_than_exactly(self):
        """Greater-than is escaped to &gt;."""
        from src.export.epub_export import escape_xml
        assert escape_xml(">") == "&gt;"
        assert escape_xml(">>") == "&gt;&gt;"

    def test_escapes_double_quote_exactly(self):
        """Double quote is escaped to &quot;."""
        from src.export.epub_export import escape_xml
        assert escape_xml('"') == "&quot;"
        assert escape_xml('""') == "&quot;&quot;"

    def test_escapes_single_quote_exactly(self):
        """Single quote is escaped to &apos;."""
        from src.export.epub_export import escape_xml
        assert escape_xml("'") == "&apos;"
        assert escape_xml("''") == "&apos;&apos;"

    def test_special_chars_at_boundaries(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("&start") == "&amp;start"
        assert escape_xml("start&") == "start&amp;"
        assert escape_xml("<end") == "&lt;end"
        assert escape_xml("end>") == "end&gt;"

    def test_consecutive_special_chars(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("a & < > \" ' b") == "a &amp; &lt; &gt; &quot; &apos; b"

    def test_not_idempotent_runs_twice(self):
        """Running escape_xml twice double-escapes — it is not idempotent."""
        from src.export.epub_export import escape_xml
        once = escape_xml("a & b")
        twice = escape_xml(once)
        # Second pass escapes the & in &amp; to &amp;amp;
        assert twice == "a &amp;amp; b"
        assert once != twice

    def test_preserves_normal_text(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("Hello World") == "Hello World"

    def test_escapes_empty_string(self):
        from src.export.epub_export import escape_xml
        assert escape_xml("") == ""


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

    def test_converts_bold_and_italic_combined(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("***bold italic***")
        assert "<strong>" in result
        assert "<em>bold italic</em>" not in result  # closing tag is </strong></em>
        # The bold comes before italic in nesting
        assert result.index("<strong>") < result.index("<em>")
        # The content appears between the tags
        assert "bold italic" in result

    def test_links_not_converted(self):
        """Markdown links pass through unchanged as plain text in a paragraph."""
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("See [this](https://example.com)")
        # Links are not converted to <a> tags — they stay as markdown text
        assert "<a>" not in result
        assert "[this](https://example.com)" in result
        assert "<p>" in result

    def test_paragraph_without_trailing_newline(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("Just plain text")
        assert "<p>Just plain text</p>" in result

    def test_empty_string_returns_empty(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("")
        assert result == ""

    def test_plain_text_becomes_paragraph(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("Plain text without formatting")
        assert result.startswith("<p>")
        assert "</p>" in result

    def test_header_then_paragraph(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("# Header\n\nParagraph")
        assert "<h1>Header</h1>" in result
        assert "<p>Paragraph</p>" in result

    def test_multiple_consecutive_headers(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("# H1\n## H2\n### H3")
        assert "<h1>H1</h1>" in result
        assert "<h2>H2</h2>" in result
        assert "<h3>H3</h3>" in result

    def test_bold_inside_paragraph(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("This is **bold** text")
        assert "<p>This is <strong>bold</strong> text</p>" in result

    def test_italic_inside_paragraph(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("This is *italic* text")
        assert "<p>This is <em>italic</em> text</p>" in result

    def test_multiple_paragraphs_separated_by_empty_line(self):
        from src.export.epub_export import convert_markdown_to_xhtml
        result = convert_markdown_to_xhtml("Para one\n\nPara two")
        assert "<p>Para one</p>" in result
        assert "<p>Para two</p>" in result


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

    def test_seed_at_start_of_prompt(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("A dragon awakens", "fantasy")
        # Seed appears at the very start of the prompt
        assert result.startswith("A dragon awakens")

    def test_includes_style(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("A dragon awakens", style="fantasy")
        assert "fantasy" in result.lower() or "Style:" in result

    def test_fantasy_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("magic", style="fantasy")
        fantasy_desc = GENRE_STYLES["fantasy"]
        # The fantasy description should appear in the prompt
        assert fantasy_desc in result

    def test_scifi_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("space", style="scifi")
        assert GENRE_STYLES["scifi"] in result

    def test_thriller_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("danger", style="thriller")
        assert GENRE_STYLES["thriller"] in result

    def test_romance_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("love", style="romance")
        assert GENRE_STYLES["romance"] in result

    def test_mystery_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("clue", style="mystery")
        assert GENRE_STYLES["mystery"] in result

    def test_horror_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("fear", style="horror")
        assert GENRE_STYLES["horror"] in result

    def test_literary_style(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("life", style="literary")
        assert GENRE_STYLES["literary"] in result

    def test_unknown_style_defaults_to_fantasy(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        result = build_cover_prompt("something", style="unknown")
        assert GENRE_STYLES["fantasy"] in result

    def test_includes_style_line(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("test", style="fantasy")
        # Prompt should have a "Style:" section
        lines = result.split("\n")
        style_lines = [l for l in lines if l.startswith("Style:")]
        assert len(style_lines) == 1

    def test_includes_requirements_section(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("test", style="fantasy")
        # Prompt should have a "Requirements:" section
        assert "Requirements:" in result
        # Requirements should be hyphen-prefixed
        lines = result.split("\n")
        req_lines = [l for l in lines if l.startswith("- ")]
        assert len(req_lines) >= 4

    def test_requirement_vertical_format(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("test")
        assert "Vertical book cover" in result or "2:3" in result

    def test_requirement_no_text(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("test")
        # Requirement to have no text/title on the cover
        assert "No text" in result or "no text" in result

    def test_truncates_long_seed(self):
        from src.export.cover_art import build_cover_prompt
        long_seed = "x" * 1000
        result = build_cover_prompt(long_seed)
        # The seed is embedded in prompt, total length is bounded
        assert len(result) < 2000

    def test_empty_seed_included(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("", "fantasy")
        # Empty seed should still produce valid prompt with style + requirements
        assert "Style:" in result
        assert "Requirements:" in result

    def test_seed_with_markdown_preserved(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("A **dragon** awakens", "fantasy")
        # Markdown in seed is preserved (not stripped)
        assert "**dragon**" in result

    def test_seed_with_special_chars(self):
        from src.export.cover_art import build_cover_prompt
        result = build_cover_prompt("A dragon & a phoenix: it's epic!", "fantasy")
        assert "A dragon & a phoenix: it's epic!" in result

    def test_all_genre_styles_present(self):
        from src.export.cover_art import build_cover_prompt, GENRE_STYLES
        for genre in GENRE_STYLES:
            result = build_cover_prompt("test seed", style=genre)
            assert GENRE_STYLES[genre] in result, f"Genre {genre} style not in prompt"


class TestExportManuscriptTxt:
    """Tests for src.export.export.export_manuscript_txt()."""

    def test_export_basic_txt(self, mock_manuscript_md, tmp_path):
        """Mocked Path.read_text is called and content is written."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.exists", return_value=True):
            with patch("src.export.export.Path.read_text") as mock_read:
                with patch("src.export.export.Path.write_text") as mock_write:
                    mock_read.return_value = (
                        "# My Novel\n\n## Chapter 1\n\n"
                        "This is **bold** and *italic*.\n\n"
                        "[Link](https://example.com)"
                    )
                    result = export_manuscript_txt(tmp_path)

                    assert "txt_path" in result
                    assert "word_count" in result
                    assert mock_write.called

    def test_removes_markdown_headers(self, tmp_path):
        """# and ## headers are stripped from output."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.read_text", return_value="# Title\n\n## Section\n\ncontent"):
            with patch("src.export.export.Path.write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "# Title" not in written
                assert "## Section" not in written
                assert "content" in written

    def test_removes_bold_formatting(self, tmp_path):
        """**bold** becomes just 'bold' in output."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.read_text", return_value="This is **bold** text"):
            with patch("src.export.export.Path.write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "**bold**" not in written
                assert "bold" in written

    def test_removes_italic_formatting(self, tmp_path):
        """*italic* becomes just 'italic' in output."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.read_text", return_value="This is *italic* text"):
            with patch("src.export.export.Path.write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "*italic*" not in written
                assert "italic" in written

    def test_removes_links(self, tmp_path):
        """[text](url) becomes just 'text' in output."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.read_text", return_value="Visit [my site](https://example.com) now"):
            with patch("src.export.export.Path.write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "[my site](https://example.com)" not in written
                assert "my site" in written

    def test_returns_error_when_manuscript_missing(self, tmp_path):
        """When manuscript.md does not exist, returns dict with 'error' key."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.exists", return_value=False):
            result = export_manuscript_txt(tmp_path)
            assert "error" in result

    def test_word_count_returned(self, tmp_path):
        """Result includes correct word_count for the cleaned text."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.read_text", return_value="one two three"):
            with patch("src.export.export.Path.write_text"):
                result = export_manuscript_txt(tmp_path)
                assert result["word_count"] == 3

    def test_multiple_formatting_types_removed(self, tmp_path):
        """Bold, italic, and links all removed; content preserved."""
        from src.export.export import export_manuscript_txt

        content = (
            "# Header\n\n"
            "**bold** and *italic* and [a link](https://example.com)."
        )
        with patch("src.export.export.Path.read_text", return_value=content):
            with patch("src.export.export.Path.write_text") as mock_write:
                export_manuscript_txt(tmp_path)
                written = mock_write.call_args[0][0]
                assert "**" not in written
                assert "*" not in written or "italic" not in written
                assert "[a link]" not in written
                assert "bold" in written
                assert "italic" in written
                assert "a link" in written

    def test_returns_txt_path_in_result(self, tmp_path):
        """Result dict contains 'txt_path' key pointing to output file."""
        from src.export.export import export_manuscript_txt

        with patch("src.export.export.Path.read_text", return_value="Some content"):
            with patch("src.export.export.Path.write_text"):
                result = export_manuscript_txt(tmp_path)
                assert "txt_path" in result
                assert result["txt_path"].endswith("manuscript.txt")


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
