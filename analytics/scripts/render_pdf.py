"""Render a markdown report to PDF via reportlab.

Supports the subset we use in BI reports: H1/H2/H3, paragraphs, bullet
lists, GitHub-style pipe tables, bold/italic emphasis, inline code, and
``![alt](path.png)`` images (paths resolved relative to the .md file).
Pure Python — no system dependencies on cairo/wkhtmltopdf/pandoc.

Usage:
    uv run python scripts/render_pdf.py output/<report>.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# Envio orange for headings / accents
ACCENT = colors.HexColor("#FF5722")
GREY_HEADER = colors.HexColor("#3a3a3a")
GREY_LIGHT = colors.HexColor("#eeeeee")


def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "Title", parent=base["Title"],
            fontName="Helvetica-Bold", fontSize=22, leading=26,
            textColor=ACCENT, spaceAfter=14,
        ),
        "H1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=15, leading=19,
            textColor=GREY_HEADER, spaceBefore=14, spaceAfter=8,
        ),
        "H2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=12, leading=15,
            textColor=GREY_HEADER, spaceBefore=10, spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "Body", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.5, leading=13,
            textColor=colors.black, spaceAfter=6,
            alignment=0,
        ),
        "Bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.5, leading=13,
            leftIndent=14, bulletIndent=2, spaceAfter=3,
        ),
        "Meta": ParagraphStyle(
            "Meta", parent=base["BodyText"],
            fontName="Helvetica-Oblique", fontSize=9, leading=12,
            textColor=colors.grey, spaceAfter=10,
        ),
    }
    return styles


_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


# Letter page = 8.5" wide; with 0.7" margins each side that's 7.1" of
# content width. Cap images a touch narrower for breathing room.
MAX_IMAGE_WIDTH = 6.8 * inch


def _build_image(src_path: Path) -> Image | None:
    if not src_path.exists():
        return None
    reader = ImageReader(str(src_path))
    iw, ih = reader.getSize()
    scale = min(1.0, MAX_IMAGE_WIDTH / iw)
    return Image(str(src_path), width=iw * scale, height=ih * scale)


def _inline(text: str) -> str:
    """Convert markdown inline formatting to reportlab paragraph tags.

    Order matters: code first (so we don't re-escape inside it), then
    bold, then italic. Reportlab paragraphs accept a small XML-ish
    subset including <b>, <i>, <font>.
    """
    # Escape any pre-existing < or & characters to avoid breaking the
    # mini-XML parser. Do this before adding any tags.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _INLINE_CODE.sub(
        lambda m: f'<font name="Courier" size="9">{m.group(1)}</font>', text
    )
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    return text


def _is_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|")


def _is_table_separator(line: str) -> bool:
    s = line.strip().strip("|").strip()
    if not s:
        return False
    cells = [c.strip() for c in s.split("|")]
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def _parse_table(lines: list[str], i: int) -> tuple[Table, int]:
    """Parse a pipe table starting at line i. Returns (Table, next_i)."""
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    # Lines i+1 is the separator; data follows.
    rows = [header]
    j = i + 2
    while j < len(lines) and _is_table_row(lines[j]):
        rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
        j += 1

    # Wrap each cell in a Paragraph so inline formatting + wrapping works.
    body_style = ParagraphStyle(
        "Cell", fontName="Helvetica", fontSize=8.5, leading=11,
        textColor=colors.black,
    )
    head_style = ParagraphStyle(
        "Cell", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
        textColor=colors.white,
    )
    data = []
    for r_idx, row in enumerate(rows):
        style = head_style if r_idx == 0 else body_style
        data.append([Paragraph(_inline(c), style) for c in row])

    table = Table(data, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREY_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    return table, j


def _render(md_text: str, styles: dict, base_dir: Path) -> list:
    flow = []
    lines = md_text.splitlines()
    i = 0
    title_emitted = False
    paragraph_buf: list[str] = []

    def flush_paragraph():
        if not paragraph_buf:
            return
        text = " ".join(s.strip() for s in paragraph_buf if s.strip())
        if text:
            flow.append(Paragraph(_inline(text), styles["Body"]))
        paragraph_buf.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Images: ![alt](file.png) — path is relative to the .md file
        m = _IMAGE.match(stripped)
        if m:
            flush_paragraph()
            alt, src = m.group(1), m.group(2)
            img_path = (base_dir / src).resolve()
            img = _build_image(img_path)
            if img is not None:
                flow.append(Spacer(1, 4))
                flow.append(KeepTogether([img]))
                if alt:
                    caption_style = ParagraphStyle(
                        "Caption", fontName="Helvetica-Oblique", fontSize=8.5,
                        leading=11, textColor=colors.grey, alignment=1, spaceAfter=8,
                    )
                    flow.append(Paragraph(_inline(alt), caption_style))
                else:
                    flow.append(Spacer(1, 8))
            else:
                flow.append(Paragraph(
                    _inline(f"[missing image: {src}]"), styles["Meta"]
                ))
            i += 1
            continue

        # Tables
        if _is_table_row(line) and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            flush_paragraph()
            tbl, i = _parse_table(lines, i)
            flow.append(Spacer(1, 4))
            flow.append(tbl)
            flow.append(Spacer(1, 8))
            continue

        # Headings
        if stripped.startswith("# "):
            flush_paragraph()
            text = stripped[2:].strip()
            if not title_emitted:
                flow.append(Paragraph(_inline(text), styles["Title"]))
                title_emitted = True
            else:
                flow.append(Paragraph(_inline(text), styles["H1"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            flow.append(Paragraph(_inline(stripped[3:].strip()), styles["H1"]))
            i += 1
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            flow.append(Paragraph(_inline(stripped[4:].strip()), styles["H2"]))
            i += 1
            continue

        # Bullets
        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            flow.append(
                Paragraph(_inline(stripped[2:].strip()), styles["Bullet"], bulletText="•")
            )
            i += 1
            continue

        # Italic-only metadata line (e.g. "*Clean lifetime volume excludes...*")
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            flush_paragraph()
            flow.append(
                Paragraph(stripped.strip("*"), styles["Meta"])
            )
            i += 1
            continue

        # Blank line ends a paragraph
        if not stripped:
            flush_paragraph()
            i += 1
            continue

        paragraph_buf.append(line)
        i += 1

    flush_paragraph()
    return flow


def render(md_path: Path, pdf_path: Path | None = None) -> Path:
    if pdf_path is None:
        pdf_path = md_path.with_suffix(".pdf")
    md_text = md_path.read_text()
    styles = _build_styles()
    flow = _render(md_text, styles, base_dir=md_path.resolve().parent)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=md_path.stem.replace("_", " ").title(),
    )
    doc.build(flow)
    return pdf_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: render_pdf.py <markdown-path> [pdf-path]")
        sys.exit(1)
    md = Path(sys.argv[1])
    pdf = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    out = render(md, pdf)
    print(f"Rendered: {out}")


if __name__ == "__main__":
    main()
