"""Generate Bhapi Competitive & Strategic Analysis PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

# ── Brand colours ──────────────────────────────────────────────
ORANGE = HexColor("#FF6B35")
TEAL = HexColor("#0D9488")
DARK = HexColor("#1F2937")
GRAY = HexColor("#6B7280")
LIGHT_GRAY = HexColor("#F3F4F6")
LIGHT_BG = HexColor("#FFF7F3")
WHITE = white

# SWOT quadrant colours
SWOT_GREEN = HexColor("#D1FAE5")
SWOT_YELLOW = HexColor("#FEF3C7")
SWOT_BLUE = HexColor("#DBEAFE")
SWOT_RED = HexColor("#FEE2E2")
SWOT_GREEN_HDR = HexColor("#059669")
SWOT_YELLOW_HDR = HexColor("#D97706")
SWOT_BLUE_HDR = HexColor("#2563EB")
SWOT_RED_HDR = HexColor("#DC2626")

# Gartner quadrant colours
Q_LEADER = HexColor("#D1FAE5")
Q_CHALLENGER = HexColor("#DBEAFE")
Q_VISIONARY = HexColor("#FEF3C7")
Q_NICHE = HexColor("#F3F4F6")

LOGO_PATH = os.path.join(os.path.dirname(__file__), "portal", "public", "logo.png")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Bhapi_Competitive_Analysis.pdf")

WIDTH, HEIGHT = A4


# ── Styles ─────────────────────────────────────────────────────
def build_styles():
    styles = getSampleStyleSheet()
    defs = [
        ("CoverTitle", "Helvetica-Bold", 30, DARK, 0, 36, TA_LEFT),
        ("CoverSubtitle", "Helvetica", 14, GRAY, 20, 18, TA_LEFT),
        ("CoverDate", "Helvetica", 11, GRAY, 8, 14, TA_LEFT),
        ("SH1", "Helvetica-Bold", 20, ORANGE, 12, 26, TA_LEFT),
        ("SH2", "Helvetica-Bold", 14, TEAL, 10, 18, TA_LEFT),
        ("SH3", "Helvetica-Bold", 11, DARK, 6, 14, TA_LEFT),
        ("BodyText2", "Helvetica", 9.5, DARK, 4, 13, TA_LEFT),
        ("BodySmall", "Helvetica", 8.5, GRAY, 3, 11, TA_LEFT),
        ("BulletItem", "Helvetica", 9.5, DARK, 2, 13, TA_LEFT),
        ("TableHead", "Helvetica-Bold", 8, WHITE, 0, 11, TA_CENTER),
        ("TableCell", "Helvetica", 7.5, DARK, 0, 10, TA_LEFT),
        ("TableCellC", "Helvetica", 7.5, DARK, 0, 10, TA_CENTER),
        ("FooterStyle", "Helvetica", 8, GRAY, 0, 10, TA_CENTER),
        ("QuadLabel", "Helvetica-Bold", 8, DARK, 0, 10, TA_CENTER),
        ("QuadVendor", "Helvetica", 7, DARK, 0, 9, TA_LEFT),
        ("SWOTHead", "Helvetica-Bold", 10, WHITE, 0, 13, TA_CENTER),
        ("SWOTCell", "Helvetica", 8, DARK, 0, 11, TA_LEFT),
        ("BannerTitle", "Helvetica-Bold", 18, WHITE, 0, 22, TA_CENTER),
        ("BannerSub", "Helvetica", 10, WHITE, 0, 14, TA_CENTER),
    ]
    for name, font, size, color, after, leading, align in defs:
        styles.add(ParagraphStyle(
            name, fontName=font, fontSize=size, textColor=color,
            spaceAfter=after, leading=leading, alignment=align,
        ))
    return styles


# ── Helpers ────────────────────────────────────────────────────
def bullet(text, styles):
    return Paragraph(f'<font color="#FF6B35">\u25cf</font>  {text}', styles["BulletItem"])


def section_banner(title, subtitle, styles, w):
    data = [
        [Paragraph(title, styles["BannerTitle"])],
        [Paragraph(subtitle, styles["BannerSub"])],
    ]
    t = Table(data, colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def make_table(header, rows, col_widths, styles):
    """Standard comparison table with orange header."""
    hdr = [Paragraph(h, styles["TableHead"]) for h in header]
    body = []
    for row in rows:
        body.append([Paragraph(str(c), styles["TableCell"]) for c in row])
    data = [hdr] + body
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        bg = WHITE if i % 2 == 1 else LIGHT_GRAY
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def check():
    return '<font color="#059669">\u2713</font>'


def cross():
    return '<font color="#DC2626">\u2717</font>'


def partial():
    return '<font color="#D97706">\u25d0</font>'


def swot_table(strengths, weaknesses, opportunities, threats, styles, w):
    """2x2 SWOT quadrant table."""
    def cell_content(items, style_name):
        lines = "<br/>".join(f"\u2022 {i}" for i in items)
        return Paragraph(lines, styles[style_name])

    half = w / 2 - 2
    data = [
        [Paragraph("<b>STRENGTHS</b>", styles["SWOTHead"]),
         Paragraph("<b>WEAKNESSES</b>", styles["SWOTHead"])],
        [cell_content(strengths, "SWOTCell"),
         cell_content(weaknesses, "SWOTCell")],
        [Paragraph("<b>OPPORTUNITIES</b>", styles["SWOTHead"]),
         Paragraph("<b>THREATS</b>", styles["SWOTHead"])],
        [cell_content(opportunities, "SWOTCell"),
         cell_content(threats, "SWOTCell")],
    ]
    t = Table(data, colWidths=[half, half])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), SWOT_GREEN_HDR),
        ("BACKGROUND", (1, 0), (1, 0), SWOT_YELLOW_HDR),
        ("BACKGROUND", (0, 2), (0, 2), SWOT_BLUE_HDR),
        ("BACKGROUND", (1, 2), (1, 2), SWOT_RED_HDR),
        ("BACKGROUND", (0, 1), (0, 1), SWOT_GREEN),
        ("BACKGROUND", (1, 1), (1, 1), SWOT_YELLOW),
        ("BACKGROUND", (0, 3), (0, 3), SWOT_BLUE),
        ("BACKGROUND", (1, 3), (1, 3), SWOT_RED),
        ("GRID", (0, 0), (-1, -1), 1, WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def gartner_quadrant(title, vendors, styles, w):
    """
    Render a Gartner-style Magic Quadrant as a labelled 2x2 grid with vendors.
    vendors: list of (name, quadrant, rationale) where quadrant is
             'leader'|'challenger'|'visionary'|'niche'
    """
    leaders = [v for v in vendors if v[1] == "leader"]
    challengers = [v for v in vendors if v[1] == "challenger"]
    visionaries = [v for v in vendors if v[1] == "visionary"]
    niche = [v for v in vendors if v[1] == "niche"]

    def vendor_cell(vlist):
        if not vlist:
            return Paragraph("", styles["QuadVendor"])
        lines = "<br/>".join(f"<b>\u25cf {v[0]}</b> \u2014 {v[2]}" for v in vlist)
        return Paragraph(lines, styles["QuadVendor"])

    half = w / 2 - 2
    # Y-axis label concept: Ability to Execute (top) / Completeness of Vision (right)
    data = [
        [Paragraph("<b>CHALLENGERS</b>", styles["QuadLabel"]),
         Paragraph("<b>LEADERS</b>", styles["QuadLabel"])],
        [vendor_cell(challengers), vendor_cell(leaders)],
        [Paragraph("<b>NICHE PLAYERS</b>", styles["QuadLabel"]),
         Paragraph("<b>VISIONARIES</b>", styles["QuadLabel"])],
        [vendor_cell(niche), vendor_cell(visionaries)],
    ]
    t = Table(data, colWidths=[half, half])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 1), Q_CHALLENGER),
        ("BACKGROUND", (1, 0), (1, 1), Q_LEADER),
        ("BACKGROUND", (0, 2), (0, 3), Q_NICHE),
        ("BACKGROUND", (1, 2), (1, 3), Q_VISIONARY),
        ("GRID", (0, 0), (-1, -1), 1, WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("SPAN", (0, 0), (0, 0)),
        ("SPAN", (1, 0), (1, 0)),
        ("SPAN", (0, 2), (0, 2)),
        ("SPAN", (1, 2), (1, 2)),
    ]))
    return t


# ── PDF Builder ────────────────────────────────────────────────
def build_pdf():
    styles = build_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    W = doc.width
    story = []

    # ───────────────────────────────────────────────────────────
    # COVER PAGE
    # ───────────────────────────────────────────────────────────
    logo = Image(LOGO_PATH, width=50 * mm, height=26.5 * mm)
    logo.hAlign = "LEFT"
    story.append(logo)
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Competitive &amp; Strategic Analysis", styles["CoverTitle"]))
    story.append(Paragraph(
        "Bhapi App &amp; Bhapi AI Portal \u2014 Market Positioning, Gap Analysis, SWOT &amp; Magic Quadrant",
        styles["CoverSubtitle"],
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("March 2026  \u2022  Confidential", styles["CoverDate"]))
    story.append(HRFlowable(width="100%", thickness=3, color=ORANGE, spaceAfter=12))
    story.append(Spacer(1, 8 * mm))

    # Table of contents
    toc_items = [
        "1. Executive Summary",
        "2. Product Overview",
        "3. Competitive Landscape \u2014 Bhapi App",
        "4. Competitive Landscape \u2014 Bhapi AI Portal",
        "5. Gap Analysis",
        "6. SWOT Analysis \u2014 Bhapi App",
        "7. SWOT Analysis \u2014 Bhapi AI Portal",
        "8. Combined Ecosystem SWOT",
        "9. Gartner-Style Magic Quadrant Analysis",
        "10. Pricing Comparison",
        "11. Strategic Recommendations",
        "12. Appendix: Competitor Profiles",
    ]
    toc_data = [[Paragraph("<b>Table of Contents</b>", styles["SH2"])]]
    for item in toc_items:
        toc_data.append([Paragraph(item, styles["BodyText2"])])
    toc = Table(toc_data, colWidths=[W * 0.7])
    toc.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(toc)
    story.append(Spacer(1, 8 * mm))

    # Key metrics box
    metrics = [
        ["<b>Bhapi App</b>", "<b>Bhapi AI Portal (bhapi.ai)</b>"],
        ["iOS &amp; Android safe social networking", "AI safety monitoring for families/schools/clubs"],
        ["60+ mobile features, 40+ back-office features", "19 modules, ~190 routes, 1,314 tests, 30+ pages"],
        ["Toxicity detection, SafeSearch, Video Intelligence", "14 risk categories, 10 AI platforms, deepfake detection"],
        ["WebSocket messaging, content moderation portal", "Browser extension (Chrome/Firefox/Safari), SIS/SSO"],
    ]
    metrics_data = [[Paragraph(c, styles["BodySmall"]) for c in row] for row in metrics]
    mt = Table(metrics_data, colWidths=[W / 2, W / 2])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(mt)
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 1. EXECUTIVE SUMMARY
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))
    exec_paras = [
        "The Bhapi ecosystem consists of two complementary products targeting the family digital safety market \u2014 a space projected to reach $8.2B by 2028 (CAGR 11.3%). <b>Bhapi App</b> provides a safe social networking environment with real-time content moderation, while <b>Bhapi AI Portal</b> (bhapi.ai) addresses the emerging and largely unserved niche of AI-specific safety monitoring.",
        "<b>Key Finding 1:</b> The family safety market is dominated by device-level monitoring tools (Bark, Qustodio, Net Nanny). None offer AI-specific risk monitoring, giving Bhapi AI Portal a clear first-mover advantage in the AI safety sub-segment.",
        "<b>Key Finding 2:</b> Bhapi App competes in a crowded parental controls space but differentiates through its unique combination of a purpose-built safe social network (not just monitoring overlaid on existing platforms) with Google-powered toxicity scoring, SafeSearch, and Video Intelligence.",
        "<b>Key Finding 3:</b> The education AI safety market is nascent. Current players (Securly, GoGuardian, Gaggle) focus on web filtering and crisis detection. None monitor AI-specific platforms or provide deepfake/emotional dependency detection, positioning Bhapi AI Portal for rapid adoption.",
        "<b>Strategic Opportunity:</b> Cross-product integration (App users get AI Portal lite, Portal users discover the safe social network) creates a flywheel that no competitor can replicate with a single product.",
    ]
    for p in exec_paras:
        story.append(Paragraph(p, styles["BodyText2"]))
        story.append(Spacer(1, 2 * mm))
    story.append(Spacer(1, 4 * mm))

    # Market context box
    story.append(Paragraph("Market Context", styles["SH2"]))
    market_hdr = ["Metric", "Value", "Source / Note"]
    market_rows = [
        ["Global parental control market", "$3.2B (2024)", "Growing at 11.3% CAGR to $8.2B by 2028"],
        ["US households with children online", "46 million", "75% concerned about AI interactions (2025 survey)"],
        ["K-12 EdTech safety market", "$1.8B (2024)", "Driven by CIPA compliance and mental health mandates"],
        ["Children using AI chatbots (US)", "42% of 13\u201317 year-olds", "Pew Research, Dec 2024"],
        ["AI companion app downloads", "300M+ in 2025", "Character.AI, Replika, Pi leading growth"],
        ["EU AI Act enforcement", "Aug 2026", "Creates mandatory compliance requirements"],
        ["School AI safety budget (avg)", "$2\u20135/student/yr", "Embedded in existing safety/filtering budgets"],
    ]
    story.append(make_table(market_hdr, market_rows, [100, 80, W - 180], styles))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 2. PRODUCT OVERVIEW
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("2. Product Overview", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Side-by-side comparison of the two Bhapi products, highlighting their complementary positioning.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 3 * mm))

    overview_hdr = ["Dimension", "Bhapi App", "Bhapi AI Portal"]
    overview_rows = [
        ["Target Market", "Families seeking a safe social network for children", "Parents, schools &amp; clubs monitoring children\u2019s AI usage"],
        ["Core Value Prop", "Safe-by-design social media with real-time content moderation", "AI safety governance across 10 AI platforms"],
        ["Platforms", "iOS, Android, Web (back-office)", "Web portal, Chrome/Firefox/Safari extension"],
        ["Key Features", "Toxicity detection, SafeSearch, Video Intelligence, WebSocket messaging, content moderation portal", "14 risk categories, deepfake detection, emotional dependency, SIS/SSO, EU AI Act compliance, time budgets"],
        ["Tech Stack", "React Native + Node.js + Google Cloud AI", "FastAPI + Next.js + PostgreSQL + Stripe"],
        ["Content Analysis", "Google Perspective API (toxicity), Cloud Vision (SafeSearch), Video Intelligence", "AI risk taxonomy (14 categories), PII detection, safety scores (0\u2013100)"],
        ["Moderation Model", "Automated scoring + human moderator queue with auto-assignment", "Automated alerts + parent/admin review + blocking rules"],
        ["Monetisation", "Freemium (in development)", "Family $9.99/mo, School per-seat, Enterprise custom"],
        ["Status", "Live (iOS/Android)", "v2.1.0 Post-MVP complete, 1,314 tests passing"],
    ]
    story.append(make_table(overview_hdr, overview_rows, [60, W / 2 - 30, W / 2 - 30], styles))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 3. COMPETITIVE LANDSCAPE \u2014 BHAPI APP
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("3. Competitive Landscape \u2014 Bhapi App", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Bhapi App competes in the family safety / parental controls market. Unlike competitors that overlay monitoring on existing platforms, Bhapi provides a purpose-built safe social network.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Feature Comparison Matrix", styles["SH2"]))
    story.append(Spacer(1, 2 * mm))
    ck = check()
    cr = cross()
    pt = partial()
    app_hdr = ["Feature", "Bhapi App", "Bark", "Qustodio", "Net Nanny", "Canopy", "Family Link"]
    app_cols = [80, 52, 52, 52, 52, 52, 52]
    app_rows = [
        ["Safe social network", ck, cr, cr, cr, cr, cr],
        ["AI toxicity scoring", ck, pt, cr, cr, cr, cr],
        ["SafeSearch (images)", ck, ck, ck, ck, ck, pt],
        ["Video content analysis", ck, cr, cr, cr, cr, cr],
        ["Real-time messaging", ck, cr, cr, cr, cr, cr],
        ["Content mod. portal", ck, ck, pt, pt, cr, cr],
        ["Auto-assign moderators", ck, cr, cr, cr, cr, cr],
        ["Multi-device monitoring", cr, ck, ck, ck, pt, ck],
        ["App-level blocking", cr, ck, ck, ck, ck, ck],
        ["Screen time controls", cr, ck, ck, ck, pt, ck],
        ["Location tracking", cr, ck, ck, cr, cr, ck],
        ["Social media monitoring", pt, ck, ck, pt, cr, cr],
        ["SMS/call monitoring", cr, ck, pt, cr, cr, cr],
    ]
    story.append(make_table(app_hdr, app_rows, app_cols, styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Bhapi App Differentiators", styles["SH2"]))
    for d in [
        "<b>Purpose-built safe social network</b> \u2014 Children interact in a controlled environment rather than being monitored on uncontrolled platforms. This is fundamentally different from monitoring-overlay approaches.",
        "<b>Google-powered content analysis pipeline</b> \u2014 Three-layer analysis (Perspective API toxicity + Cloud Vision SafeSearch + Video Intelligence) with configurable thresholds provides enterprise-grade moderation.",
        "<b>Automated moderator assignment</b> \u2014 Posts flagged by AI are automatically assigned to the moderator with the lightest workload, ensuring consistent review times.",
        "<b>WebSocket real-time messaging</b> \u2014 1-on-1 and group chat with reactions, presence indicators, and full message search \u2014 comparable to mainstream social apps but in a safe environment.",
        "<b>Post status workflow</b> \u2014 Public \u2192 Pending \u2192 Blocked \u2192 Draft lifecycle with re-analysis on edits. No other parental control offers this content pipeline sophistication.",
    ]:
        story.append(bullet(d, styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Competitive Position Summary", styles["SH2"]))
    story.append(Paragraph(
        "Bhapi App occupies a unique position as the only <b>purpose-built safe social network</b> in the family safety market. "
        "While competitors like Bark and Qustodio overlay monitoring on existing platforms (Instagram, TikTok, Snapchat), "
        "Bhapi creates a controlled social environment where content safety is engineered into the platform itself. "
        "This is analogous to the difference between adding security cameras to a public park versus building a private, supervised playground.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "The trade-off is clear: Bhapi App does not monitor activity on other platforms. This limits its appeal for families "
        "where children already use mainstream social media. However, for families with younger children (ages 8\u201313) who have "
        "not yet joined mainstream platforms, Bhapi offers a compelling \u201cfirst social network\u201d value proposition that "
        "competitors cannot match.",
        styles["BodyText2"],
    ))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 4. COMPETITIVE LANDSCAPE \u2014 BHAPI AI PORTAL
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("4. Competitive Landscape \u2014 Bhapi AI Portal", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Bhapi AI Portal operates at the intersection of family safety and AI governance \u2014 a segment that established players have not yet addressed. School-focused competitors offer web filtering but lack AI-specific monitoring.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Feature Comparison Matrix", styles["SH2"]))
    story.append(Spacer(1, 2 * mm))
    portal_hdr = ["Feature", "Bhapi AI", "Bark", "Securly", "GoGuardian", "Gaggle", "Lightspeed"]
    portal_cols = [82, 50, 50, 50, 50, 50, 50]
    portal_rows = [
        ["AI platform monitoring (10)", ck, cr, cr, cr, cr, cr],
        ["14-category risk taxonomy", ck, cr, cr, cr, cr, cr],
        ["Deepfake detection", ck, cr, cr, cr, cr, cr],
        ["Emotional dependency", ck, cr, cr, cr, cr, cr],
        ["Browser extension", ck, cr, ck, ck, cr, ck],
        ["EU AI Act compliance", ck, cr, cr, cr, cr, cr],
        ["SIS integration (Clever)", ck, cr, ck, ck, ck, ck],
        ["SSO (Google/Entra)", ck, cr, ck, ck, pt, ck],
        ["Family tier pricing", ck, ck, cr, cr, cr, cr],
        ["School per-seat pricing", ck, cr, ck, ck, ck, ck],
        ["Time budgets/bedtime", ck, ck, cr, cr, cr, pt],
        ["AI literacy modules", ck, cr, cr, cr, cr, cr],
        ["Web content filtering", pt, ck, ck, ck, pt, ck],
        ["Device-level monitoring", cr, ck, ck, ck, pt, ck],
        ["24/7 crisis support", cr, cr, cr, cr, ck, cr],
        ["Hardware products", cr, ck, cr, cr, cr, ck],
    ]
    story.append(make_table(portal_hdr, portal_rows, portal_cols, styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Bhapi AI Portal Differentiators", styles["SH2"]))
    for d in [
        "<b>AI-specific monitoring across 10 platforms</b> \u2014 ChatGPT, Gemini, Copilot, Claude, Grok, Character.AI, Replika, Pi, Perplexity, Poe. No competitor monitors AI platforms at all.",
        "<b>14-category AI risk taxonomy</b> \u2014 Purpose-built classification system covering AI-specific risks (hallucination exposure, prompt injection attempts, data leakage) beyond generic content categories.",
        "<b>Deepfake &amp; emotional dependency detection</b> \u2014 Integration with Hive/Sensity for deepfake analysis and proprietary emotional dependency scoring for AI companion apps.",
        "<b>EU AI Act compliance framework</b> \u2014 Built-in transparency, human review, and appeals workflows meeting EU AI Act requirements. First-mover for regulatory compliance in family AI safety.",
        "<b>AI literacy education</b> \u2014 5 educational modules with quizzes and progress tracking, turning safety monitoring into a learning opportunity.",
    ]:
        story.append(bullet(d, styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Competitive Position Summary", styles["SH2"]))
    story.append(Paragraph(
        "Bhapi AI Portal is a <b>category creator</b> in AI-specific safety monitoring. No existing competitor \u2014 whether in the "
        "family safety or EdTech safety space \u2014 monitors AI platforms directly. Securly and GoGuardian filter web content broadly "
        "but cannot inspect AI conversations for risk patterns like emotional dependency, academic integrity violations, or data leakage.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "The 14-category AI risk taxonomy represents significant domain expertise that would take competitors 12\u201318 months to "
        "replicate. The browser extension monitoring 10 AI platforms simultaneously is technically non-trivial and creates a "
        "data advantage: as more families use the Portal, risk classification accuracy improves through pattern recognition.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "The primary risk is that established players (Bark, Securly) add AI monitoring features. However, their architectures "
        "are built for device-level and web-level monitoring, not AI conversation analysis. Bolting on AI monitoring would "
        "require fundamental product changes, providing Bhapi a 12\u201324 month window of competitive advantage.",
        styles["BodyText2"],
    ))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 5. GAP ANALYSIS
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("5. Gap Analysis", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Critical Gaps (High Priority)", styles["SH2"]))
    gap_crit_hdr = ["Gap", "Product", "Impact", "Competitors With", "Effort"]
    gap_crit_rows = [
        ["Mobile app for AI Portal", "AI Portal", "Parents expect mobile-first experience; web-only limits adoption", "Bark, Qustodio", "High"],
        ["Native device management", "Both", "Cannot control device settings, app installs, or screen time at OS level", "Bark, Qustodio, Net Nanny, Family Link", "Very High"],
        ["App store presence", "AI Portal", "Discoverability limited without app store listings", "All major competitors", "Medium"],
        ["Multi-device monitoring", "App", "Families use multiple devices; single-app scope limits coverage", "Bark, Qustodio, Net Nanny", "High"],
    ]
    story.append(make_table(gap_crit_hdr, gap_crit_rows, [72, 48, 140, 80, 48], styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Moderate Gaps", styles["SH2"]))
    gap_mod_hdr = ["Gap", "Product", "Impact", "Priority"]
    gap_mod_rows = [
        ["Network effect / user base", "App", "Safe social network value grows with users; cold-start challenge", "High"],
        ["Enterprise sales team", "AI Portal", "School/enterprise deals require sales motion, not just self-serve", "Medium"],
        ["SOC 2 Type II certification", "Both", "Enterprise buyers require compliance certifications", "Medium"],
        ["Location tracking", "App", "Common parental control feature; absence noted by prospects", "Low"],
        ["SMS/call monitoring", "App", "Standard in Bark/Qustodio; less relevant for safe-network model", "Low"],
        ["24/7 human crisis support", "AI Portal", "Gaggle\u2019s key differentiator; resource-intensive to match", "Low"],
    ]
    story.append(make_table(gap_mod_hdr, gap_mod_rows, [82, 52, 200, 52], styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Feature Parity Analysis vs Key Competitors", styles["SH2"]))
    story.append(Spacer(1, 2 * mm))
    parity_hdr = ["Feature Area", "Bhapi App vs Bark", "Bhapi AI vs Securly", "Action Required"]
    parity_rows = [
        ["Device monitoring", "Bark covers 30+ apps; Bhapi covers own platform only", "Securly does web filtering; Bhapi does AI analysis", "Different models \u2014 not directly comparable"],
        ["Mobile app", "Both have mobile apps", "Securly has apps; Bhapi is web-only", "AI Portal mobile app needed Q2 2026"],
        ["Content analysis", "Bhapi has deeper AI scoring; Bark has broader coverage", "Bhapi has 14 AI categories; Securly has web categories", "Bhapi advantage in depth; gap in breadth"],
        ["School integrations", "Bark free for schools; Bhapi has no school tier", "Both have SIS; Securly has more districts", "Sales motion needed for school adoption"],
        ["Hardware", "Bark has Bark Phone; Bhapi has none", "Lightspeed has relay appliances", "Not a priority \u2014 focus on software moat"],
        ["Crisis response", "Neither has 24/7 human review", "Gaggle has crisis team; Bhapi has automated alerts", "Consider partnership for human review"],
        ["Compliance", "Neither has EU AI Act features", "Neither has EU AI Act features", "Bhapi AI Portal has strong advantage"],
    ]
    story.append(make_table(parity_hdr, parity_rows, [62, 100, 100, 126], styles))
    story.append(PageBreak())

    story.append(Paragraph("Prioritised Gap Closure Roadmap", styles["SH2"]))
    road_hdr = ["Phase", "Timeline", "Action", "Expected Impact"]
    road_rows = [
        ["Phase 1", "Q2 2026", "AI Portal mobile app (React Native)", "2\u20133x family adoption increase"],
        ["Phase 1", "Q2 2026", "App store listings (iOS + Android)", "Discoverability, organic installs"],
        ["Phase 2", "Q3 2026", "Cross-product bundling (App + Portal)", "Unique value prop, lower churn"],
        ["Phase 2", "Q3 2026", "SOC 2 Type II engagement", "Unlock enterprise pipeline"],
        ["Phase 3", "Q4 2026", "Device-level management SDK", "Feature parity with Bark/Qustodio"],
        ["Phase 3", "Q1 2027", "Enterprise sales hire + partnerships", "Scale school/district adoption"],
    ]
    story.append(make_table(road_hdr, road_rows, [48, 52, 170, 118], styles))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 6. SWOT \u2014 BHAPI APP
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("6. SWOT Analysis \u2014 Bhapi App", styles["SH1"]))
    story.append(Spacer(1, 3 * mm))
    story.append(swot_table(
        strengths=[
            "Purpose-built safe social network (unique positioning)",
            "Three-layer Google AI content analysis pipeline",
            "Automated moderator workload balancing",
            "Real-time WebSocket messaging with reactions",
            "Comprehensive back-office moderation portal",
            "Sub-account management for families",
        ],
        weaknesses=[
            "No multi-device monitoring (single-app scope)",
            "No device-level controls (screen time, app blocking)",
            "Cold-start / network effect challenge",
            "No location tracking or geofencing",
            "Limited to Bhapi platform (not cross-app monitoring)",
            "Monetisation model not yet finalised",
        ],
        opportunities=[
            "Growing parental concern about children\u2019s social media use",
            "Regulatory push (COPPA 2.0, EU Digital Services Act)",
            "Cross-product integration with Bhapi AI Portal",
            "School/club partnerships for group deployments",
            "White-label opportunity for youth organisations",
            "AI-powered personalised safety recommendations",
        ],
        threats=[
            "Bark\u2019s market dominance and brand recognition",
            "Apple/Google expanding built-in parental controls",
            "Network effect barrier (children prefer popular platforms)",
            "Regulatory changes could mandate device-level controls",
            "Larger competitors could add safe social features",
            "User fatigue with yet another social platform",
        ],
        styles=styles, w=W,
    ))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 7. SWOT \u2014 BHAPI AI PORTAL
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("7. SWOT Analysis \u2014 Bhapi AI Portal", styles["SH1"]))
    story.append(Spacer(1, 3 * mm))
    story.append(swot_table(
        strengths=[
            "First-mover in AI-specific safety monitoring",
            "14-category risk taxonomy (industry-leading depth)",
            "Monitors 10 AI platforms via browser extension",
            "Deepfake detection integration (Hive/Sensity)",
            "Emotional dependency scoring (unique capability)",
            "EU AI Act compliance framework built-in",
            "SIS/SSO integrations (Clever, ClassLink, Google, Entra)",
            "Comprehensive: family + school + club tiers",
        ],
        weaknesses=[
            "Web-only (no mobile app yet)",
            "Browser extension required (friction for non-technical parents)",
            "No device-level monitoring",
            "Limited brand awareness vs established players",
            "Small team relative to well-funded competitors",
            "Extension cannot monitor native mobile AI apps",
        ],
        opportunities=[
            "AI safety is a new, rapidly growing concern for parents",
            "Schools urgently seeking AI governance tools",
            "EU AI Act creates compliance demand",
            "No direct competitor in AI-specific family safety",
            "Partnership with school districts (SIS integrations ready)",
            "AI companion apps (Character.AI, Replika) raising alarm",
            "Enterprise AI governance adjacent market",
        ],
        threats=[
            "Bark/Securly could add AI monitoring features",
            "AI platforms could add built-in parental controls",
            "Browser extension model vulnerable to platform changes",
            "Rapid AI platform proliferation (new platforms to support)",
            "Privacy backlash against monitoring tools",
            "Well-funded EdTech competitors entering AI safety",
        ],
        styles=styles, w=W,
    ))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 8. COMBINED ECOSYSTEM SWOT
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("8. Combined Ecosystem SWOT", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "The Bhapi ecosystem\u2019s combined strength is greater than either product alone. Cross-product synergies create defensible advantages that single-product competitors cannot easily replicate.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(swot_table(
        strengths=[
            "Two-product moat: safe social + AI safety monitoring",
            "Full-spectrum safety: social content + AI interactions",
            "Shared user base across products (cross-sell)",
            "Technical depth: Google AI + custom risk taxonomy",
            "Both B2C (family) and B2B (school) channels",
            "Regulatory alignment (COPPA, GDPR, EU AI Act)",
        ],
        weaknesses=[
            "Two products to maintain with limited resources",
            "No native device-level controls on either product",
            "Brand awareness challenge across two markets",
            "Integration between products not yet built",
            "Mobile gap in AI Portal limits cross-product value",
        ],
        opportunities=[
            "Bundle pricing creates unique value proposition",
            "App users naturally convert to AI Portal as children start using AI",
            "School partnerships can drive both products simultaneously",
            "Platform for third-party safety modules (marketplace)",
            "Data insights across both products improve safety algorithms",
            "Acquisition target for larger safety/EdTech companies",
        ],
        threats=[
            "Resource dilution across two products",
            "Platform risk: Apple/Google/AI platform policy changes",
            "Competitor consolidation (Bark acquires AI safety startup)",
            "Market confusion: two products may dilute brand message",
            "Regulatory fragmentation across jurisdictions",
        ],
        styles=styles, w=W,
    ))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 9. GARTNER-STYLE MAGIC QUADRANT ANALYSIS
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("9. Gartner-Style Magic Quadrant Analysis", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Positioning is based on <b>Ability to Execute</b> (vertical axis: product maturity, market presence, resources) "
        "and <b>Completeness of Vision</b> (horizontal axis: innovation, strategy, market understanding). "
        "Vendors placed using publicly available product and market data as of March 2026.",
        styles["BodyText2"],
    ))
    story.append(Spacer(1, 4 * mm))

    # Quadrant 1: Family Safety
    story.append(Paragraph("Family Safety Market", styles["SH2"]))
    story.append(Spacer(1, 1 * mm))
    # Axes annotation
    story.append(Paragraph(
        '<font color="#6B7280">\u2191 Ability to Execute &nbsp;&nbsp;&nbsp;&nbsp; Completeness of Vision \u2192</font>',
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 1 * mm))
    story.append(gartner_quadrant(
        "Family Safety",
        vendors=[
            ("Bark", "leader", "Market leader with broadest device coverage and brand recognition"),
            ("Qustodio", "leader", "Strong cross-platform monitoring with 30+ social platform support"),
            ("Net Nanny", "challenger", "Established brand, solid content filtering, but aging innovation"),
            ("Google Family Link", "challenger", "Massive distribution via Android, but limited to Google ecosystem"),
            ("Canopy", "visionary", "AI image filtering pioneer, sexting prevention, but smaller scale"),
            ("Bhapi App", "visionary", "Unique safe social network model with advanced AI content analysis"),
            ("Screen Time Labs", "niche", "Focused rewards system, limited safety features"),
        ],
        styles=styles, w=W,
    ))
    story.append(Spacer(1, 6 * mm))

    # Quadrant 2: AI Safety for Education
    story.append(Paragraph("AI Safety for Education Market", styles["SH2"]))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(
        '<font color="#6B7280">\u2191 Ability to Execute &nbsp;&nbsp;&nbsp;&nbsp; Completeness of Vision \u2192</font>',
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 1 * mm))
    story.append(gartner_quadrant(
        "AI Safety for Education",
        vendors=[
            ("Securly", "leader", "Longest-learning AI filter, strong school penetration, but no AI platform monitoring"),
            ("GoGuardian", "leader", "Classroom management + mental health, large install base"),
            ("Lightspeed Systems", "challenger", "SSL decryption and hardware, enterprise-only focus"),
            ("Gaggle", "challenger", "24/7 crisis support with human reviewers, but email/Drive focused"),
            ("Bhapi AI Portal", "visionary", "Only vendor monitoring AI platforms specifically; 14-category taxonomy, deepfake detection"),
            ("Bark (Education)", "niche", "Family product extended to schools, limited AI-specific features"),
        ],
        styles=styles, w=W,
    ))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Positioning Rationale", styles["SH2"]))
    story.append(Spacer(1, 2 * mm))
    rationale_hdr = ["Vendor", "Market", "Quadrant", "Rationale"]
    rationale_rows = [
        ["Bark", "Family Safety", "Leader", "Broadest device/platform coverage, strongest brand, hardware + software + school tiers"],
        ["Qustodio", "Family Safety", "Leader", "Best cross-platform monitoring, freemium model drives acquisition, mature product"],
        ["Net Nanny", "Family Safety", "Challenger", "Established brand with decades of content filtering data, but innovation has stalled"],
        ["Google Family Link", "Family Safety", "Challenger", "Massive Android distribution, but limited features and no iOS monitoring"],
        ["Canopy", "Family Safety", "Visionary", "AI image filtering is forward-looking, but limited scale and integrations"],
        ["Bhapi App", "Family Safety", "Visionary", "Unique safe social network model with sophisticated AI analysis; limited device coverage"],
        ["Securly", "AI Safety/EdTech", "Leader", "Longest-learning AI filter, strong school penetration, comprehensive platform"],
        ["GoGuardian", "AI Safety/EdTech", "Leader", "Full classroom suite, mental health alerts, dominant in Chromebook schools"],
        ["Lightspeed", "AI Safety/EdTech", "Challenger", "Enterprise-grade infrastructure, but complex and expensive"],
        ["Gaggle", "AI Safety/EdTech", "Challenger", "Unique human crisis team, proven life-saving impact, but narrow scope"],
        ["Bhapi AI Portal", "AI Safety/EdTech", "Visionary", "Only vendor with AI-specific monitoring, 14-category taxonomy, deepfake detection"],
        ["Bark (Education)", "AI Safety/EdTech", "Niche", "Family product extended to schools, free tier limits features"],
    ]
    story.append(make_table(rationale_hdr, rationale_rows, [62, 60, 56, 210], styles))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 10. PRICING COMPARISON
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("10. Pricing Comparison", styles["SH1"]))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Family Tier Pricing", styles["SH2"]))
    story.append(Spacer(1, 2 * mm))
    price_fam_hdr = ["Provider", "Monthly", "Annual", "Free Tier", "Key Inclusions"]
    price_fam_rows = [
        ["Bhapi AI Portal", "$9.99/mo", "~$120/yr", "14-day trial", "AI monitoring, 10 platforms, extension, alerts, literacy"],
        ["Bark Premium", "$14/mo", "$99/yr", "7-day trial", "Multi-device, location, content monitoring, screen time"],
        ["Bark Jr", "$5/mo", "$49/yr", "7-day trial", "Location, screen time, app management (no content monitoring)"],
        ["Qustodio Basic", "Free", "Free", "Yes (1 device)", "Basic web filtering, activity reports"],
        ["Qustodio Premium", "~$5\u20138/mo", "$55\u2013100/yr", "3-day trial", "5\u201315 devices, social monitoring, location, SOS button"],
        ["Net Nanny", "~$4\u201311/mo", "$50\u2013130/yr", "14-day guarantee", "1\u201320 devices, content filtering, screen time, profanity masking"],
        ["Canopy", "$10\u201316/mo", "~$96\u2013192/yr", "Free trial", "AI image filtering, sexting prevention, screen time"],
        ["Google Family Link", "Free", "Free", "Yes", "Android/Chrome only: app management, screen time, location"],
    ]
    story.append(make_table(price_fam_hdr, price_fam_rows, [68, 52, 56, 52, 160], styles))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("School / Enterprise Tier Pricing", styles["SH2"]))
    story.append(Spacer(1, 2 * mm))
    price_sch_hdr = ["Provider", "Pricing Model", "Approx. Cost", "Key Inclusions"]
    price_sch_rows = [
        ["Bhapi AI Portal", "Per-seat (self-serve Stripe)", "Custom", "AI monitoring, SIS integration, RBAC, compliance, analytics"],
        ["Securly", "Per-student, district contract", "$2\u20135/student/yr", "Web filter, awareness, on-call crisis team"],
        ["GoGuardian", "Per-license, annual contract", "$5\u20138/student/yr", "Classroom, beacon, fleet management"],
        ["Gaggle", "Per-student, annual contract", "$3.80\u20136/student/yr", "24/7 crisis monitoring, therapy referrals"],
        ["Lightspeed", "Per-device or per-student", "Custom", "SSL inspect, classroom management, alerts, MDM"],
        ["Bark for Schools", "Free for schools", "Free", "Content monitoring on G-Suite/O365 (limited features)"],
    ]
    story.append(make_table(price_sch_hdr, price_sch_rows, [70, 82, 72, 164], styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Pricing Analysis", styles["SH3"]))
    for p in [
        "Bhapi AI Portal\u2019s $9.99/mo family tier is <b>competitively positioned</b> between Bark Premium ($14/mo) and budget options. The 14-day trial exceeds Bark\u2019s 7-day window.",
        "The AI-specific monitoring capability has <b>no direct price comparison</b> \u2014 competitors do not offer this feature set, supporting premium positioning.",
        "School tier pricing should target the <b>$3\u20136/student/yr range</b> to compete with Gaggle and undercut GoGuardian, while highlighting unique AI monitoring capabilities.",
    ]:
        story.append(bullet(p, styles))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 11. STRATEGIC RECOMMENDATIONS
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("11. Strategic Recommendations", styles["SH1"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Top 5 Near-Term Priorities (Q2\u2013Q3 2026)", styles["SH2"]))
    near = [
        ("<b>1. Launch AI Portal mobile app</b> \u2014 Critical gap. Parents expect mobile-first. React Native shared codebase with Bhapi App reduces effort. Target: Q2 2026."),
        ("<b>2. App store presence for both products</b> \u2014 Discoverability is table stakes. App Store Optimisation (ASO) for \u201cAI safety\u201d and \u201cfamily safety\u201d keywords."),
        ("<b>3. Cross-product integration pilot</b> \u2014 Bhapi App users see AI Portal alerts for their children\u2019s AI usage. Single sign-on across products. Unique ecosystem value."),
        ("<b>4. School district sales motion</b> \u2014 SIS integrations (Clever, ClassLink) are built. Target 10 pilot schools with free deployment. Convert to paid in Q3."),
        ("<b>5. SOC 2 Type II engagement</b> \u2014 Start the audit process now. Schools and enterprise buyers require it. 6\u20129 month process means Q4 completion."),
    ]
    for n in near:
        story.append(bullet(n, styles))
        story.append(Spacer(1, 1 * mm))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Top 3 Long-Term Strategic Moves (2027+)", styles["SH2"]))
    long_term = [
        ("<b>1. Platform play</b> \u2014 Open an SDK/API for third-party safety modules (e.g., specialist eating disorder detection, gambling detection). Become the safety platform, not just a product."),
        ("<b>2. Enterprise AI governance pivot</b> \u2014 The same risk taxonomy and monitoring infrastructure applies to enterprise AI usage policies. Adjacent $4B market (Gartner)."),
        ("<b>3. International expansion with regulatory moat</b> \u2014 EU AI Act compliance is already built. Expand to EU markets where competitors have not yet adapted to regulatory requirements."),
    ]
    for lt in long_term:
        story.append(bullet(lt, styles))
        story.append(Spacer(1, 1 * mm))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Cross-Product Integration Opportunities", styles["SH2"]))
    cross_prod = [
        ("<b>Unified family dashboard</b> \u2014 Single view showing social activity (App) and AI usage (Portal) for each child."),
        ("<b>Shared alert system</b> \u2014 Toxicity detected in App posts correlates with AI conversation risk scores in Portal."),
        ("<b>Bundle pricing</b> \u2014 App + Portal at $14.99/mo (vs $9.99 Portal-only) drives average revenue per user (ARPU) while providing unique cross-product value."),
        ("<b>Shared identity</b> \u2014 Single Bhapi account, SSO across products, unified child profiles with combined safety scores."),
        ("<b>Content moderation synergy</b> \u2014 Moderators reviewing App content gain AI interaction context from Portal, enabling more informed decisions."),
    ]
    for c in cross_prod:
        story.append(bullet(c, styles))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────
    # 12. APPENDIX: COMPETITOR PROFILES
    # ───────────────────────────────────────────────────────────
    story.append(Paragraph("12. Appendix: Competitor Profiles", styles["SH1"]))
    story.append(Spacer(1, 3 * mm))

    profiles = [
        ("Bark", "$5\u201314/mo or $49\u201399/yr",
         "Market-leading family safety platform monitoring 30+ apps, email, and SMS across Android, iOS, and Amazon devices. Also offers Bark Phone (custom hardware) and free school monitoring. Strongest brand recognition in the space.",
         "Broadest platform coverage, hardware product line, free school tier for acquisition",
         "No AI-specific monitoring, premium pricing, limited international presence"),

        ("Qustodio", "$55\u2013100/yr (free basic tier)",
         "Cross-platform parental control with the widest social media monitoring on Android (30+ platforms). Offers web filtering, screen time, location tracking, and SOS panic button. Available on Windows, Mac, Android, iOS, and Kindle.",
         "Best cross-platform coverage, freemium model for acquisition, strong web filtering",
         "Android-heavy feature set (iOS limited), complex pricing tiers, no AI monitoring"),

        ("Net Nanny", "$50\u2013130/yr",
         "Pioneer in content filtering (founded 1993). Dynamic content analysis, profanity masking, and screen time management. Known for granular website categorisation. Acquired by Zift (later rebranded).",
         "Decades of content filtering data, strong brand legacy, solid content categorisation",
         "Aging innovation, no AI monitoring, limited social media features, basic approach"),

        ("Canopy", "$10\u201316/mo",
         "Newer entrant focused on AI-powered image filtering and sexting prevention. Uses machine learning to detect inappropriate images in real-time. Strong privacy-first messaging.",
         "AI image analysis, privacy-first approach, modern UX design",
         "Smaller market share, fewer integrations, no AI platform monitoring, limited school features"),

        ("Google Family Link", "Free",
         "Google\u2019s built-in parental controls for Android and Chrome. App management, screen time limits, location sharing. Pre-installed on Android devices, massive distribution advantage.",
         "Free, massive distribution, native OS integration, location sharing",
         "Android/Chrome only, basic features, no content monitoring, no AI safety"),

        ("Securly", "Custom (per-student)",
         "K-12 web filtering leader with the \u201clongest-learning AI\u201d content classifier. Offers awareness (student wellbeing monitoring), on-call crisis team, and school-wide analytics. Strong district-level sales.",
         "Longest-learning AI filter, strong school penetration, crisis team, analytics",
         "No family tier, no AI platform monitoring, school-only, complex procurement"),

        ("GoGuardian", "Custom (per-license)",
         "Comprehensive EdTech platform: classroom management (GoGuardian Teacher), web filtering (GoGuardian Admin), mental health (GoGuardian Beacon), and fleet management. Strong in Chromebook schools.",
         "Full classroom suite, mental health alerts, Chromebook dominance, large install base",
         "Chrome-centric, no family tier, no AI platform monitoring, expensive per-seat"),

        ("Gaggle", "$3.80\u20136/student/yr",
         "Unique model: monitors student G-Suite and Office 365 content with 24/7 human review crisis team. Claims to have identified 1,500+ students exhibiting suicidal behaviour. Therapy referral partnerships.",
         "24/7 human crisis support, proven life-saving track record, therapy referrals",
         "Email/Drive focused only, no web filtering, no real-time monitoring, no AI safety"),

        ("Lightspeed Systems", "Custom",
         "Enterprise-grade school safety platform with SSL decryption, classroom management, hardware relay appliances, and MDM integration. Focuses on large districts with complex infrastructure needs.",
         "Enterprise features, SSL inspection, hardware integration, comprehensive MDM",
         "Enterprise-only, no family tier, complex deployment, high cost, no AI monitoring"),
    ]

    for name, pricing, desc, strengths, weaknesses in profiles:
        story.append(Paragraph(f"{name}", styles["SH2"]))
        story.append(Paragraph(f"<b>Pricing:</b> {pricing}", styles["BodySmall"]))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(desc, styles["BodyText2"]))
        story.append(Paragraph(f'<font color="#059669"><b>Strengths:</b></font> {strengths}', styles["BodySmall"]))
        story.append(Paragraph(f'<font color="#DC2626"><b>Weaknesses:</b></font> {weaknesses}', styles["BodySmall"]))
        story.append(Spacer(1, 3 * mm))

    # ───────────────────────────────────────────────────────────
    # CLOSING CTA
    # ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    cta_data = [
        [Paragraph("Build safer digital communities with Bhapi", styles["BannerTitle"])],
        [Paragraph("bhapi.ai  \u2022  Bhapi App (iOS &amp; Android)  \u2022  Contact us for a demo", styles["BannerSub"])],
    ]
    cta = Table(cta_data, colWidths=[W])
    cta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cta)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "\u00a9 2026 Bhapi  \u2022  bhapi.ai  \u2022  Confidential \u2014 For Internal &amp; Investor Use",
        styles["FooterStyle"],
    ))

    # ── Page template ──────────────────────────────────────────
    def first_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(WIDTH / 2, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def later_pages(canvas, doc):
        canvas.saveState()
        canvas.drawImage(
            LOGO_PATH, 18 * mm, HEIGHT - 12 * mm,
            width=24 * mm, height=12.7 * mm,
            preserveAspectRatio=True, mask="auto",
        )
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(WIDTH / 2, 10 * mm, f"Page {doc.page}")
        canvas.drawRightString(
            WIDTH - 18 * mm, 10 * mm,
            "Bhapi Competitive & Strategic Analysis \u2022 March 2026",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    print(f"PDF generated: {OUTPUT_PATH}")
    print(f"Pages: Open the PDF to verify ~18-20 pages")


if __name__ == "__main__":
    build_pdf()
