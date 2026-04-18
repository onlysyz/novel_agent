"""LaTeX Typesetting for PDF Export.

Generates a print-ready LaTeX manuscript from chapters.
Includes professional formatting, chapter styles, and proper typography.
"""

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.common.api import get_client

NOVEL_DIR = Path(".")
LATEX_TEMPLATE = r"""\documentclass[12pt,letterpaper,openany]{{book}}
\usepackage[margin=1in, top=1in, bottom=1in]{{geometry}}
\usepackage{{times}}
\usepackage{{indentfirst}}
\usepackage{{titling}}
\usepackage{{tocloft}}
\usepackage{{chapstyle}}

% Title page
\pretitle{{\begin{{center}}\LARGE\MakeUppercase}}
\posttitle{{\end{{center}}\vskip 1em}}
\preauthor{{\begin{{center}}\Large}}
\postauthor{{\end{{center}}}}
\predate{{\begin{{center}}\large}}
\postdate{{\end{{center}}}}

% Chapter formatting
\usepackage{{setspace}}
\setstretch{{1.15}}

% Paragraph spacing
\parindent 1em
\parskip 0pt plus 0.1em

% Page headers
\usepackage{{fancyhdr}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot[C]{{\thepage}}
renewcommand{{\chaptermark}}[1]{{%
  \markboth{{\MakeUppercase{{#1}}}}{{}}}}

% Hyphenation
\hyphenation{{}}

\begin{{document}}

\title{{{title}}}
\author{{{author}}}
\date{{}}

\maketitle
\thispagestyle{{empty}}
\newpage

\tableofcontents
\newpage

{dedication}

{body}

\end{{document}}
"""

CHAPTER_TEMPLATE = r"""
\chapter{{{chapter_title}}}
{chapter_content}
"""


def sanitize_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    # Order matters - escape backslashes first
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def convert_markdown_to_latex(markdown_text: str) -> str:
    """Convert basic markdown to LaTeX."""
    lines = markdown_text.split("\n")
    result = []
    in_paragraph = False
    in_code_block = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                result.append("\\end{verbatim}")
                in_code_block = False
            else:
                result.append("\\begin{verbatim}")
                in_code_block = True
            continue

        if in_code_block:
            result.append(line)
            continue

        # Headers
        if line.startswith("# "):
            if in_paragraph:
                result.append("\n\\par\n")
                in_paragraph = False
            result.append(f"\\section*{{{line[2:].strip()}}}")
        elif line.startswith("## "):
            if in_paragraph:
                result.append("\n\\par\n")
                in_paragraph = False
            result.append(f"\\subsection*{{{line[3:].strip()}}}")
        elif line.startswith("### "):
            if in_paragraph:
                result.append("\n\\par\n")
                in_paragraph = False
            result.append(f"\\subsubsection*{{{line[4:].strip()}}}")

        # Horizontal rule
        elif line.strip() in ["---", "***", "___"]:
            if in_paragraph:
                result.append("\n\\par\n")
                in_paragraph = False
            result.append("\\hrulefill")

        # Empty line
        elif not line.strip():
            if in_paragraph:
                result.append("\n\\par\n")
                in_paragraph = False

        # Regular paragraph
        else:
            # Handle bold/italic
            line = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", line)
            line = re.sub(r"\*(.+?)\*", r"\\textit{\1}", line)
            line = re.sub(r"_(.+?)_", r"\\textit{\1}", line)

            # Handle quotes
            line = re.sub(r'"([^"]+)"', r"`\\ quo t\\'e{}", line)
            line = re.sub(r"'([^']+)'", r"`\\ quo t\\'e{}", line)

            if not in_paragraph:
                result.append(line)
                in_paragraph = True
            else:
                result.append(" " + line)

    if in_paragraph:
        result.append("\n\\par\n")

    return "".join(result)


def load_chapters() -> list[tuple[int, str, str]]:
    """Load all chapters from the chapters directory."""
    chapters_dir = NOVEL_DIR / "chapters"
    if not chapters_dir.exists():
        return []

    chapters = []
    for entry in sorted(chapters_dir.glob("ch_*.md")):
        # Skip revised versions for now
        if "_revised" in entry.stem:
            continue

        num_str = entry.stem.replace("ch_", "")
        try:
            num = int(num_str)
        except ValueError:
            continue

        content = entry.read_text()

        # Check for revised version
        revised_path = chapters_dir / f"ch_{num:02}_revised.md"
        if revised_path.exists():
            content = revised_path.read_text()

        # Extract title from first heading
        title = f"Chapter {num}"
        for line in content.split("\n"):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                break

        # Remove title from content for LaTeX
        content = re.sub(r"^# .+?\n", "", content, count=1)

        chapters.append((num, title, content))

    return chapters


def get_novel_metadata() -> dict:
    """Extract metadata from project files."""
    metadata = {
        "title": "Untitled Novel",
        "author": "NovelForge",
        "dedication": "",
        "seed": "",
    }

    # Get title from outline or seed
    seed_path = NOVEL_DIR / "seed.txt"
    if seed_path.exists():
        metadata["seed"] = seed_path.read_text().strip()

    outline_path = NOVEL_DIR / "outline.md"
    if outline_path.exists():
        outline = outline_path.read_text()
        # Try to extract title
        title_match = re.search(r"#\s+(.+?)\n", outline)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

    return metadata


def generate_latex(
    output_path: Optional[str] = None,
    template: Optional[str] = None,
) -> dict:
    """
    Generate LaTeX manuscript from chapters.

    Args:
        output_path: Path for the .tex output file
        template: Optional custom LaTeX template

    Returns:
        dict with paths to generated files
    """
    chapters = load_chapters()
    if not chapters:
        return {"error": "No chapters found"}

    metadata = get_novel_metadata()

    # Build dedication page if we have seed
    dedication = ""
    if metadata["seed"]:
        dedication = f"""
\\newpage
\\thispagestyle{{empty}}
\\vfill
\\begin{{center}}
\\textit{{Based on the concept:}}
\\textit{{"{metadata["seed"]}"}}
\\end{{center}}
\\vfill
\\newpage
"""

    # Build chapter content
    body_parts = []
    for num, title, content in chapters:
        latex_content = convert_markdown_to_latex(content)
        latex_title = sanitize_latex(title)
        chapter_latex = CHAPTER_TEMPLATE.format(
            chapter_title=latex_title,
            chapter_content=latex_content,
        )
        body_parts.append(chapter_latex)

    body = "\n".join(body_parts)

    # Use template or default
    latex_doc = template or LATEX_TEMPLATE

    # Fill template
    latex_doc = latex_doc.format(
        title=metadata["title"],
        author=metadata["author"],
        dedication=dedication,
        body=body,
    )

    # Write output
    if output_path is None:
        output_path = str(NOVEL_DIR / "manuscript.tex")

    Path(output_path).write_text(latex_doc)

    print(f"LaTeX manuscript written to: {output_path}")

    return {
        "tex_path": output_path,
        "title": metadata["title"],
        "chapter_count": len(chapters),
    }


def compile_pdf(tex_path: str, output_dir: Optional[str] = None) -> dict:
    """
    Compile LaTeX to PDF using pdflatex.

    Requires: pdflatex (install via MacTeX on macOS)

    Args:
        tex_path: Path to the .tex file
        output_dir: Directory for PDF output

    Returns:
        dict with paths to generated files
    """
    import subprocess

    tex_path = Path(tex_path)
    if not tex_path.exists():
        return {"error": f"TeX file not found: {tex_path}"}

    if output_dir is None:
        output_dir = tex_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Check for pdflatex
    try:
        subprocess.run(
            ["pdflatex", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "error": "pdflatex not found. Install MacTeX (macOS) or texlive (Linux).",
            "tex_path": str(tex_path),
        }

    # Compile twice for TOC
    base_name = tex_path.stem
    for _ in range(2):
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={output_dir}",
                str(tex_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {
                "error": f"pdflatex failed:\n{result.stderr[-1000:]}",
                "tex_path": str(tex_path),
            }

    pdf_path = output_dir / f"{base_name}.pdf"
    if not pdf_path.exists():
        return {
            "error": "PDF not generated",
            "tex_path": str(tex_path),
        }

    print(f"PDF written to: {pdf_path}")

    return {
        "pdf_path": str(pdf_path),
        "tex_path": str(tex_path),
    }


if __name__ == "__main__":
    result = generate_latex()
    print(result)
