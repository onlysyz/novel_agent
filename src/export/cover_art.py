"""Cover Art Generation.

Generates book cover art using fal.ai API.
Creates themed covers based on the novel's concept and genre.
"""

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

NOVEL_DIR = Path(".")

# Default cover styles by genre
GENRE_STYLES = {
    "fantasy": "epic fantasy book cover, dramatic lighting, ornate border, gold lettering",
    "scifi": "science fiction book cover, minimalist design, futuristic typography",
    "thriller": "thriller book cover, dark moody atmosphere, sharp contrast",
    "romance": "romance book cover, soft lighting, elegant typography",
    "mystery": "mystery book cover, vintage aesthetic, muted colors",
    "horror": "horror book cover, dark atmosphere, unsettling imagery",
    "literary": "literary fiction cover, minimal design, sophisticated typography",
}

# Fallback cover prompts if no seed is provided
DEFAULT_PROMPTS = [
    "mysterious ancient book on wooden desk, dramatic lighting, fog, cinematic",
    "open book with glowing pages, fantasy atmosphere, ethereal light",
    "old leather-bound book, weathered pages, candlelight, warm tones",
]


def get_seed_prompt() -> Optional[str]:
    """Extract a cover-relevant description from the seed."""
    seed_path = NOVEL_DIR / "seed.txt"
    if not seed_path.exists():
        return None

    seed = seed_path.read_text().strip()
    if not seed:
        return None

    # Limit length for API
    return seed[:500]


def build_cover_prompt(seed: str, style: str = "fantasy") -> str:
    """Build a cover art prompt from seed and style."""
    base_style = GENRE_STYLES.get(style, GENRE_STYLES["fantasy"])

    prompt = f"""{seed}

Style: {base_style}

Requirements:
- Vertical book cover format (2:3 aspect ratio)
- No text or title on the cover
- Cinematic lighting
- Professional book cover quality
- Dark atmospheric background
- Central focal point
"""
    return prompt.strip()


def generate_cover(
    output_path: Optional[str] = None,
    style: str = "fantasy",
    width: int = 800,
    height: int = 1200,
) -> dict:
    """
    Generate cover art using fal.ai.

    Args:
        output_path: Path for the cover image output
        style: Genre style (fantasy, scifi, thriller, etc.)
        width: Image width
        height: Image height

    Returns:
        dict with paths and status
    """
    api_key = os.getenv("FAL_API_KEY")
    if not api_key:
        return {
            "error": "FAL_API_KEY not set. Get your key at https://fal.ai",
            "available_styles": list(GENRE_STYLES.keys()),
        }

    seed = get_seed_prompt()
    if not seed:
        seed = "A mysterious novel waiting to be discovered"

    prompt = build_cover_prompt(seed, style)

    if output_path is None:
        output_path = str(NOVEL_DIR / "cover.png")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import json
        import urllib.request

        # Call fal.ai API
        request_body = json.dumps({
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
        }).encode()

        request = urllib.request.Request(
            "https://fal.run/fal-ai/flux/schnell",
            data=request_body,
            headers={
                "Authorization": f"Key {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode())

        if "images" in result and result["images"]:
            image_url = result["images"][0]["url"]

            # Download the image
            img_request = urllib.request.Request(
                image_url,
                headers={"User-Agent": "NovelForge/1.0"},
            )
            with urllib.request.urlopen(img_request, timeout=60) as img_response:
                output_path.write_bytes(img_response.read())

            print(f"Cover art written to: {output_path}")
            return {
                "cover_path": str(output_path),
                "prompt": prompt,
                "style": style,
            }
        else:
            return {"error": "No images returned from fal.ai"}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"error": f"fal.ai HTTP error {e.code}: {error_body}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def generate_simple_cover(output_path: Optional[str] = None) -> dict:
    """
    Generate a simple programmatic cover without AI.

    Creates a styled cover with the novel title using PIL.

    Args:
        output_path: Path for the cover image

    Returns:
        dict with paths
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        if output_path is None:
            output_path = str(NOVEL_DIR / "cover.png")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create image
        width, height = 800, 1200
        img = Image.new("RGB", (width, height), color="#1a1a2e")
        draw = ImageDraw.Draw(img)

        # Try to load a font, fall back to default
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Times.ttc", 72)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Times.ttc", 36)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = title_font

        # Get title
        title = "Untitled Novel"
        seed_path = NOVEL_DIR / "seed.txt"
        if seed_path.exists():
            seed = seed_path.read_text().strip()
            if seed:
                # Use first line of seed as title
                title = seed.split("\n")[0][:50]

        # Draw decorative border
        border_color = "#e94560"
        border_width = 10
        draw.rectangle(
            [border_width, border_width, width - border_width, height - border_width],
            outline=border_color,
            width=border_width
        )

        # Draw title
        bbox = draw.textbbox((0, 0), title, font=title_font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, height // 2 - 100), title, fill="#ffffff", font=title_font)

        # Draw subtitle
        subtitle = "A NovelForge Production"
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = bbox[2] - bbox[0]
        sub_x = (width - sub_width) // 2
        draw.text((sub_x, height // 2 + 50), subtitle, fill="#888888", font=subtitle_font)

        # Draw decorative line
        line_y = height // 2 + 120
        draw.line(
            [(width // 4, line_y), (3 * width // 4, line_y)],
            fill=border_color,
            width=3
        )

        img.save(output_path, "PNG")
        print(f"Simple cover written to: {output_path}")

        return {
            "cover_path": str(output_path),
            "title": title,
            "simple": True,
        }

    except ImportError:
        return {
            "error": "PIL (Pillow) not installed. Install with: pip install pillow",
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    result = generate_simple_cover()
    print(result)
