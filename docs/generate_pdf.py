#!/usr/bin/env python3
"""
Generate professional PDF from Bhapi Gap Analysis markdown.
Uses ReportLab with Bhapi branding (orange #FF6B35, teal #0D9488).
"""

import re
import os
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DOCS_DIR = Path(__file__).parent
PROJECT_DIR = DOCS_DIR.parent
LOGO_PATH = str(PROJECT_DIR / "portal" / "public" / "logo.png")
ICON_PATH = str(PROJECT_DIR / "portal" / "public" / "icon.png")
MD_PATH = str(DOCS_DIR / "Bhapi_Gap_Analysis_Q2_2026.md")
PDF_PATH = str(DOCS_DIR / "Bhapi_Gap_Analysis_Q2_2026.pdf")

# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------
BHAPI_ORANGE = colors.HexColor("#FF6B35")
BHAPI_ORANGE_LIGHT = colors.HexColor("#FFF3ED")
BHAPI_ORANGE_DARK = colors.HexColor("#E85A25")
BHAPI_TEAL = colors.HexColor("#0D9488")
BHAPI_TEAL_LIGHT = colors.HexColor("#E6F7F5")
BHAPI_DARK = colors.HexColor("#1E293B")
BHAPI_GRAY = colors.HexColor("#64748B")
BHAPI_LIGHT_GRAY = colors.HexColor("#F1F5F9")
BHAPI_WHITE = colors.HexColor("#FFFFFF")
BHAPI_RED = colors.HexColor("#DC2626")
BHAPI_YELLOW = colors.HexColor("#F59E0B")
BHAPI_GREEN = colors.HexColor("#16A34A")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def build_styles():
    ss = getSampleStyleSheet()

    body = ParagraphStyle(
        "BodyCustom",
        parent=ss["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=BHAPI_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    bold_body = ParagraphStyle(
        "BoldBody",
        parent=body,
        fontName="Helvetica-Bold",
    )
    h1 = ParagraphStyle(
        "H1Custom",
        parent=ss["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=26,
        textColor=BHAPI_ORANGE,
        spaceAfter=10,
        spaceBefore=20,
        borderWidth=0,
        borderPadding=0,
    )
    h2 = ParagraphStyle(
        "H2Custom",
        parent=ss["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=20,
        textColor=BHAPI_DARK,
        spaceAfter=8,
        spaceBefore=16,
        borderColor=BHAPI_ORANGE,
        borderWidth=2,
        borderPadding=(0, 0, 4, 8),
    )
    h3 = ParagraphStyle(
        "H3Custom",
        parent=ss["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=BHAPI_TEAL,
        spaceAfter=6,
        spaceBefore=12,
    )
    h4 = ParagraphStyle(
        "H4Custom",
        parent=ss["Heading4"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=BHAPI_DARK,
        spaceAfter=4,
        spaceBefore=8,
    )
    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=body,
        leftIndent=16,
        bulletIndent=6,
        spaceAfter=3,
    )
    code_style = ParagraphStyle(
        "CodeCustom",
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=BHAPI_DARK,
        backColor=BHAPI_LIGHT_GRAY,
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=8,
        spaceBefore=4,
        leftIndent=8,
        rightIndent=8,
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=BHAPI_WHITE,
        alignment=TA_LEFT,
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=BHAPI_DARK,
        alignment=TA_LEFT,
    )
    toc_style = ParagraphStyle(
        "TOCEntry",
        parent=body,
        fontSize=10,
        leading=16,
        textColor=BHAPI_TEAL,
        leftIndent=8,
    )

    return {
        "body": body,
        "bold_body": bold_body,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "h4": h4,
        "bullet": bullet_style,
        "code": code_style,
        "th": table_header_style,
        "td": table_cell_style,
        "toc": toc_style,
    }


# ---------------------------------------------------------------------------
# Page templates (header/footer)
# ---------------------------------------------------------------------------
def _cover_page(canvas, doc):
    """Cover page — drawn directly on canvas."""
    canvas.saveState()

    # Orange gradient band at top
    for i in range(120):
        frac = i / 120
        r = 0xFF / 255 * (1 - frac * 0.15)
        g = 0x6B / 255 * (1 - frac * 0.15)
        b = 0x35 / 255 * (1 - frac * 0.15)
        canvas.setFillColorRGB(r, g, b)
        canvas.rect(0, PAGE_H - i * 2.2, PAGE_W, 2.2, fill=True, stroke=False)

    # Logo
    if os.path.exists(LOGO_PATH):
        logo_w = 70 * mm
        logo_h = 37 * mm
        canvas.drawImage(
            LOGO_PATH,
            (PAGE_W - logo_w) / 2,
            PAGE_H - 80 * mm,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )

    # Title
    canvas.setFont("Helvetica-Bold", 28)
    canvas.setFillColor(BHAPI_DARK)
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 115 * mm, "Comprehensive Competitive")
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 127 * mm, "Gap Analysis")

    # Subtitle
    canvas.setFont("Helvetica", 14)
    canvas.setFillColor(BHAPI_GRAY)
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 145 * mm, "Bhapi Ecosystem  |  Q2 2026")

    # Divider line
    canvas.setStrokeColor(BHAPI_ORANGE)
    canvas.setLineWidth(2)
    canvas.line(PAGE_W / 2 - 60 * mm, PAGE_H - 155 * mm, PAGE_W / 2 + 60 * mm, PAGE_H - 155 * mm)

    # Meta info
    meta_y = PAGE_H - 175 * mm
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(BHAPI_DARK)
    meta_lines = [
        "Version 1.0  |  March 17, 2026",
        "Classification: Internal — Strategic",
        "Prepared for: Bhapi Leadership Team",
    ]
    for line in meta_lines:
        canvas.drawCentredString(PAGE_W / 2, meta_y, line)
        meta_y -= 16

    # Footer bar
    canvas.setFillColor(BHAPI_ORANGE)
    canvas.rect(0, 0, PAGE_W, 12 * mm, fill=True, stroke=False)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BHAPI_WHITE)
    canvas.drawCentredString(PAGE_W / 2, 4 * mm, "CONFIDENTIAL  —  For Internal Use Only")

    canvas.restoreState()


def _header_footer(canvas, doc):
    """Standard page header + footer."""
    canvas.saveState()
    page_num = doc.page

    # Header — thin orange line
    canvas.setStrokeColor(BHAPI_ORANGE)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, PAGE_H - 14 * mm, PAGE_W - MARGIN, PAGE_H - 14 * mm)

    # Header left — icon + text
    if os.path.exists(ICON_PATH):
        canvas.drawImage(
            ICON_PATH,
            MARGIN,
            PAGE_H - 13.5 * mm,
            width=8 * mm,
            height=8 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(BHAPI_ORANGE)
    canvas.drawString(MARGIN + 10 * mm, PAGE_H - 11.5 * mm, "BHAPI")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(BHAPI_GRAY)
    canvas.drawString(MARGIN + 10 * mm + 28, PAGE_H - 11.5 * mm, "Gap Analysis Q2 2026")

    # Header right — CONFIDENTIAL
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(BHAPI_GRAY)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 11.5 * mm, "INTERNAL — CONFIDENTIAL")

    # Footer line
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)

    # Footer text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(BHAPI_GRAY)
    canvas.drawString(MARGIN, 7 * mm, "bhapi.ai")
    canvas.drawCentredString(PAGE_W / 2, 7 * mm, f"Page {page_num}")
    canvas.drawRightString(PAGE_W - MARGIN, 7 * mm, "March 2026")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Markdown → Flowable helpers
# ---------------------------------------------------------------------------

def _inline_format(text):
    """Convert markdown inline formatting to ReportLab XML."""
    # Escape XML entities first (but preserve already-converted tags)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold + italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8" color="#DC2626">\1</font>', text)
    # Links (just show text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"<u>\1</u>", text)
    # Checkboxes
    text = text.replace("- [ ]", "\u2610")
    text = text.replace("- [x]", "\u2611")
    # Emoji indicators
    text = text.replace("&amp;#x2705;", "\u2705")
    return text


def _parse_table(lines, styles):
    """Parse markdown table lines into a ReportLab Table."""
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)

    if len(rows) < 2:
        return None

    # Remove separator row (second line with dashes)
    header = rows[0]
    data_rows = [r for r in rows[1:] if not all(set(c.strip()) <= {"-", ":", " "} for c in r)]

    if not data_rows:
        return None

    # Normalize column counts
    n_cols = len(header)
    for i, row in enumerate(data_rows):
        while len(row) < n_cols:
            row.append("")
        data_rows[i] = row[:n_cols]

    # Calculate column widths
    avail = PAGE_W - 2 * MARGIN
    col_w = avail / n_cols

    # For tables with many columns, shrink text
    cell_font_size = 7.5 if n_cols <= 5 else 6.5 if n_cols <= 8 else 5.5
    header_font_size = cell_font_size + 0.5

    th_style = ParagraphStyle(
        f"TH_{id(lines)}",
        fontName="Helvetica-Bold",
        fontSize=header_font_size,
        leading=header_font_size + 2.5,
        textColor=BHAPI_WHITE,
        alignment=TA_LEFT,
    )
    td_style = ParagraphStyle(
        f"TD_{id(lines)}",
        fontName="Helvetica",
        fontSize=cell_font_size,
        leading=cell_font_size + 2.5,
        textColor=BHAPI_DARK,
        alignment=TA_LEFT,
    )

    # Build table data as Paragraphs
    table_data = []
    header_cells = [Paragraph(_inline_format(c), th_style) for c in header]
    table_data.append(header_cells)
    for row in data_rows:
        table_data.append([Paragraph(_inline_format(c), td_style) for c in row])

    col_widths = [col_w] * n_cols

    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Table style
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), BHAPI_ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), BHAPI_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BHAPI_WHITE, BHAPI_LIGHT_GRAY]),
    ]

    t.setStyle(TableStyle(ts))
    return t


def _severity_color(text):
    """Add color hint for severity keywords."""
    t = text.lower()
    if "critical" in t:
        return f'<font color="#DC2626">{text}</font>'
    if "high" in t:
        return f'<font color="#F59E0B">{text}</font>'
    if "medium" in t:
        return f'<font color="#0D9488">{text}</font>'
    if "low" in t:
        return f'<font color="#16A34A">{text}</font>'
    return text


def parse_markdown(md_text, styles):
    """Convert markdown text into a list of ReportLab flowables."""
    flowables = []
    lines = md_text.split("\n")
    i = 0
    in_code_block = False
    code_lines = []
    skip_cover_meta = True  # skip the frontmatter / title area

    while i < len(lines):
        line = lines[i]

        # Skip initial frontmatter (title, version, classification, ToC)
        if skip_cover_meta:
            if line.startswith("## 1."):
                skip_cover_meta = False
                # fall through to process this line
            else:
                i += 1
                continue

        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                code_text = "\n".join(code_lines)
                code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                code_text = code_text.replace("\n", "<br/>")
                code_text = code_text.replace(" ", "&nbsp;")
                flowables.append(Paragraph(code_text, styles["code"]))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # Blank lines
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # Tables — collect all table lines
        if "|" in stripped and stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            tbl = _parse_table(table_lines, styles)
            if tbl:
                flowables.append(Spacer(1, 4))
                flowables.append(tbl)
                flowables.append(Spacer(1, 6))
            continue

        # Headings
        if stripped.startswith("#### "):
            text = _inline_format(stripped[5:])
            flowables.append(Paragraph(text, styles["h4"]))
            i += 1
            continue
        if stripped.startswith("### "):
            text = _inline_format(stripped[4:])
            flowables.append(Paragraph(text, styles["h3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            text = _inline_format(stripped[3:])
            # Page break before major sections (except first)
            if flowables:
                flowables.append(PageBreak())
            flowables.append(Paragraph(text, styles["h2"]))
            i += 1
            continue
        if stripped.startswith("# "):
            text = _inline_format(stripped[2:])
            flowables.append(Paragraph(text, styles["h1"]))
            i += 1
            continue

        # Bullet points
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = _inline_format(stripped[2:])
            flowables.append(
                Paragraph(f"\u2022  {text}", styles["bullet"])
            )
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if m:
            num = m.group(1)
            text = _inline_format(m.group(2))
            flowables.append(
                Paragraph(f"<b>{num}.</b>  {text}", styles["bullet"])
            )
            i += 1
            continue

        # Regular paragraph
        text = _inline_format(stripped)
        flowables.append(Paragraph(text, styles["body"]))
        i += 1

    return flowables


# ---------------------------------------------------------------------------
# Build PDF
# ---------------------------------------------------------------------------
def build_pdf():
    print(f"Reading markdown from: {MD_PATH}")
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    styles = build_styles()

    # Create document
    doc = BaseDocTemplate(
        PDF_PATH,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Bhapi Ecosystem: Comprehensive Competitive Gap Analysis",
        author="Bhapi Engineering & Strategy",
        subject="Competitive Gap Analysis Q2 2026",
    )

    # Frame for cover page (empty — drawn on canvas)
    cover_frame = Frame(
        MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN,
        id="cover_frame",
    )

    # Frame for content pages
    content_frame = Frame(
        MARGIN, 18 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 40 * mm,
        id="content_frame",
    )

    cover_template = PageTemplate(
        id="cover",
        frames=[cover_frame],
        onPage=_cover_page,
    )
    content_template = PageTemplate(
        id="content",
        frames=[content_frame],
        onPage=_header_footer,
    )

    doc.addPageTemplates([cover_template, content_template])

    # Parse markdown to flowables
    print("Parsing markdown...")
    content_flowables = parse_markdown(md_text, styles)

    # Build story: cover page, then content
    story = [
        NextPageTemplate("content"),
        PageBreak(),
    ]
    story.extend(content_flowables)

    print(f"Building PDF with {len(content_flowables)} content elements...")
    doc.build(story)
    print(f"PDF created: {PDF_PATH}")

    # Report size
    size_bytes = os.path.getsize(PDF_PATH)
    if size_bytes > 1_000_000:
        print(f"File size: {size_bytes / 1_000_000:.1f} MB")
    else:
        print(f"File size: {size_bytes / 1_000:.0f} KB")


if __name__ == "__main__":
    build_pdf()
