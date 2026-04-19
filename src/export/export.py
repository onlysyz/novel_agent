"""Export Orchestrator.

Coordinates all export formats: PDF (LaTeX), ePub, TXT, and cover art.
"""

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.export.typeset import generate_latex, compile_pdf
from src.export.epub_export import generate_epub
from src.export.cover_art import generate_cover, generate_simple_cover

NOVEL_DIR = Path(".")
EXPORT_DIR = NOVEL_DIR / "export"


def export_manuscript_txt(output_dir: Optional[Path] = None) -> dict:
    """Export full manuscript as plain text."""
    if output_dir is None:
        output_dir = EXPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    manuscript_path = NOVEL_DIR / "manuscript.md"
    if not manuscript_path.exists():
        return {"error": "manuscript.md not found"}

    # Read and clean manuscript
    content = manuscript_path.read_text()

    # Remove markdown formatting for plain text
    import re
    content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)  # Headers
    content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)  # Bold
    content = re.sub(r"\*(.+?)\*", r"\1", content)  # Italic
    content = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", content)  # Links

    # Output path
    output_path = output_dir / "manuscript.txt"
    output_path.write_text(content)

    word_count = len(content.split())
    print(f"TXT written to: {output_path} ({word_count} words)")

    return {
        "txt_path": str(output_path),
        "word_count": word_count,
    }


def export_all(
    formats: Optional[list[str]] = None,
    output_dir: Optional[Path] = None,
    include_cover: bool = True,
) -> dict:
    """
    Export novel in all specified formats.

    Args:
        formats: List of formats to export ["pdf", "epub", "txt", "cover"]
                If None, exports all formats.
        output_dir: Directory for export files
        include_cover: Whether to generate cover art

    Returns:
        dict with paths to all generated files
    """
    if output_dir is None:
        output_dir = EXPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if formats is None:
        formats = ["pdf", "epub", "txt", "cover"]

    results = {}

    # Get metadata
    from src.export.typeset import get_novel_metadata
    metadata = get_novel_metadata()
    results["metadata"] = metadata

    # Export formats
    if "txt" in formats:
        print("\n[Export] Generating TXT...")
        txt_result = export_manuscript_txt(output_dir)
        results["txt"] = txt_result

    if "epub" in formats:
        print("\n[Export] Generating ePub...")
        epub_result = generate_epub(str(output_dir / "manuscript.epub"))
        results["epub"] = epub_result

    if "pdf" in formats:
        print("\n[Export] Generating LaTeX...")
        tex_result = generate_latex(str(output_dir / "manuscript.tex"))
        results["latex"] = tex_result

        if "error" not in tex_result:
            print("\n[Export] Compiling PDF (requires pdflatex)...")
            pdf_result = compile_pdf(tex_result["tex_path"], output_dir)
            results["pdf"] = pdf_result

    if "cover" in formats and include_cover:
        print("\n[Export] Generating cover art...")
        # Try AI cover first, fall back to simple
        cover_result = generate_cover(str(output_dir / "cover.png"))
        if "error" in cover_result:
            print(f"  AI cover failed ({cover_result['error']}), using simple cover...")
            cover_result = generate_simple_cover(str(output_dir / "cover.png"))
        results["cover"] = cover_result

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print()
    print("Generated files:")
    for format_name, result in results.items():
        if isinstance(result, dict) and "error" not in result:
            for key, value in result.items():
                if key.endswith("_path"):
                    print(f"  {format_name}.{key.split('_')[0]}: {value}")
        elif isinstance(result, dict) and "error" in result:
            print(f"  {format_name}: Error - {result['error']}")

    return results


def run_export() -> dict:
    """Run the default export pipeline."""
    print("Starting export...")

    results = export_all()

    return results


if __name__ == "__main__":
    results = run_export()
    print("\nResults:", results)
