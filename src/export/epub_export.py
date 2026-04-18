"""ePub Export.

Generates an ePub 2.0/3.0 ebook from chapters.
ePub is a ZIP file containing XHTML content with specific structure.
"""

import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

NOVEL_DIR = Path(".")

# ePub requires mimetype file to be first and uncompressed
EPUB_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="BookId">urn:uuid:{uuid}</dc:identifier>
    <dc:date>{date}</dc:date>
    <dc:rights>{rights}</dc:rights>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="style" href="styles.css" media-type="text/css"/>
    <item id="title-page" href="title.xhtml" media-type="application/xhtml+xml"/>
    {manifest_items}
  </manifest>
  <spine>
    <itemref idref="title-page"/>
    <itemref idref="nav"/>
    {spine_items}
  </spine>
</package>
"""

NAV_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Table of Contents</title>
  <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      {toc_items}
    </ol>
  </nav>
</body>
</html>
"""

TITLE_PAGE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
  <div class="title-page">
    <h1>{title}</h1>
    <p class="author">by {author}</p>
  </div>
</body>
</html>
"""

CHAPTER_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{chapter_title}</title>
  <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
  <chapter>
    <h1>{chapter_title}</h1>
    {chapter_content}
  </chapter>
</body>
</html>
"""

CSS_TEMPLATE = """
body {{
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1em;
  line-height: 1.6;
  margin: 1em;
  text-indent: 1em;
}}
h1 {{
  text-align: center;
  font-size: 1.5em;
  font-weight: bold;
  margin: 2em 0 1em 0;
  text-indent: 0;
}}
h2 {{
  font-size: 1.2em;
  font-weight: bold;
  margin: 1.5em 0 0.5em 0;
  text-indent: 0;
}}
p {{
  margin: 0.5em 0;
  text-indent: 1em;
}}
p.first, p.no-indent {{
  text-indent: 0;
}}
.chapter-title {{
  text-align: center;
  font-size: 1.8em;
  font-weight: bold;
  margin: 2em 0;
  text-indent: 0;
}}
.title-page {{
  text-align: center;
  margin-top: 40%;
}}
.title-page h1 {{
  font-size: 2em;
  margin-bottom: 1em;
}}
.title-page .author {{
  font-size: 1.2em;
  font-style: italic;
}}
"""


def generate_uuid() -> str:
    """Generate a UUID for the book."""
    import uuid
    return str(uuid.uuid4())


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    replacements = [
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
        ('"', "&quot;"),
        ("'", "&apos;"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def convert_markdown_to_xhtml(markdown_text: str) -> str:
    """Convert basic markdown to XHTML for ePub."""
    lines = markdown_text.split("\n")
    result = []
    in_paragraph = False
    paragraph_buffer = []

    def flush_paragraph():
        nonlocal in_paragraph, paragraph_buffer
        if paragraph_buffer:
            text = " ".join(paragraph_buffer)
            # Handle bold/italic
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
            result.append(f"<p>{text}</p>")
            paragraph_buffer = []
        in_paragraph = False

    for line in lines:
        stripped = line.strip()

        # Headers
        if stripped.startswith("# "):
            flush_paragraph()
            result.append(f"<h1>{escape_xml(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            flush_paragraph()
            result.append(f"<h2>{escape_xml(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            flush_paragraph()
            result.append(f"<h3>{escape_xml(stripped[4:])}</h3>")

        # Horizontal rule
        elif stripped in ["---", "***", "___"]:
            flush_paragraph()
            result.append("<hr/>")

        # Empty line
        elif not stripped:
            flush_paragraph()

        # Regular paragraph
        else:
            paragraph_buffer.append(escape_xml(stripped))
            in_paragraph = True

    flush_paragraph()
    return "\n".join(result)


def load_chapters() -> list[tuple[int, str, str]]:
    """Load all chapters."""
    chapters_dir = NOVEL_DIR / "chapters"
    if not chapters_dir.exists():
        return []

    chapters = []
    for entry in sorted(chapters_dir.glob("ch_*.md")):
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

        # Extract title
        title = f"Chapter {num}"
        for line in content.split("\n"):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                break

        # Remove title from content
        content = re.sub(r"^# .+?\n", "", content, count=1)

        chapters.append((num, title, content))

    return chapters


def get_metadata() -> dict:
    """Get novel metadata."""
    metadata = {
        "title": "Untitled Novel",
        "author": "NovelForge",
        "uuid": generate_uuid(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "rights": "All rights reserved",
        "description": "",
    }

    seed_path = NOVEL_DIR / "seed.txt"
    if seed_path.exists():
        metadata["description"] = seed_path.read_text().strip()[:200]

    outline_path = NOVEL_DIR / "outline.md"
    if outline_path.exists():
        outline = outline_path.read_text()
        match = re.search(r"#\s+(.+?)\n", outline)
        if match:
            metadata["title"] = match.group(1).strip()

    return metadata


def generate_epub(output_path: Optional[str] = None) -> dict:
    """
    Generate ePub from chapters.

    Args:
        output_path: Path for the .epub output file

    Returns:
        dict with paths to generated files
    """
    chapters = load_chapters()
    if not chapters:
        return {"error": "No chapters found"}

    metadata = get_metadata()

    if output_path is None:
        output_path = str(NOVEL_DIR / f"{metadata['title']}.epub".replace(" ", "_"))

    epub_path = Path(output_path)
    epub_path.parent.mkdir(parents=True, exist_ok=True)

    # Create ePub (which is a ZIP file)
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be first and uncompressed
        zf.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED
        )

        # Container info
        zf.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '  <rootfiles>\n'
            '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
            '  </rootfiles>\n'
            '</container>'
        )

        # Styles
        zf.writestr("OEBPS/styles.css", CSS_TEMPLATE)

        # Navigation (TOC)
        toc_items = []
        for num, title, _ in chapters:
            toc_items.append(f'<li><a href="chapter_{num:02}.xhtml">{escape_xml(title)}</a></li>')

        nav_xhtml = NAV_TEMPLATE.format(toc_items="\n      ".join(toc_items))
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

        # Title page
        title_xhtml = TITLE_PAGE_TEMPLATE.format(
            title=escape_xml(metadata["title"]),
            author=escape_xml(metadata["author"]),
        )
        zf.writestr("OEBPS/title.xhtml", title_xhtml)

        # Chapters
        manifest_items = []
        spine_items = []

        for num, title, content in chapters:
            xhtml = CHAPTER_TEMPLATE.format(
                chapter_title=escape_xml(title),
                chapter_content=convert_markdown_to_xhtml(content),
            )
            zf.writestr(f"OEBPS/chapter_{num:02}.xhtml", xhtml)
            manifest_items.append(f'    <item id="chapter_{num}" href="chapter_{num:02}.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.append(f'    <itemref idref="chapter_{num}"/>')

        # Content OPF
        content_opf = EPUB_TEMPLATE.format(
            title=escape_xml(metadata["title"]),
            author=escape_xml(metadata["author"]),
            uuid=metadata["uuid"],
            date=metadata["date"],
            rights=escape_xml(metadata["rights"]),
            manifest_items="\n      ".join(manifest_items),
            spine_items="\n      ".join(spine_items),
        )
        zf.writestr("OEBPS/content.opf", content_opf)

    print(f"ePub written to: {epub_path}")

    return {
        "epub_path": str(epub_path),
        "title": metadata["title"],
        "chapter_count": len(chapters),
    }


if __name__ == "__main__":
    result = generate_epub()
    print(result)
