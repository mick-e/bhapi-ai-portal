"""Generate Bhapi AI Portal marketing PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER
import os

# Brand colors
ORANGE = HexColor("#FF6B35")
TEAL = HexColor("#0D9488")
DARK = HexColor("#1F2937")
GRAY = HexColor("#6B7280")
WHITE = white

LOGO_PATH = os.path.join(os.path.dirname(__file__), "portal", "public", "logo.png")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Bhapi_AI_Features.pdf")

WIDTH, HEIGHT = A4


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "BhapiTitle", fontName="Helvetica-Bold", fontSize=28,
        textColor=DARK, spaceAfter=4, leading=34
    ))
    styles.add(ParagraphStyle(
        "BhapiSubtitle", fontName="Helvetica", fontSize=13,
        textColor=GRAY, spaceAfter=20, leading=18
    ))
    styles.add(ParagraphStyle(
        "SectionHead", fontName="Helvetica-Bold", fontSize=16,
        textColor=ORANGE, spaceBefore=18, spaceAfter=8, leading=20
    ))
    styles.add(ParagraphStyle(
        "FeatureTitle", fontName="Helvetica-Bold", fontSize=11,
        textColor=DARK, spaceAfter=2, leading=14
    ))
    styles.add(ParagraphStyle(
        "FeatureDesc", fontName="Helvetica", fontSize=9.5,
        textColor=GRAY, spaceAfter=0, leading=13
    ))
    styles.add(ParagraphStyle(
        "Footer", fontName="Helvetica", fontSize=8,
        textColor=GRAY, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "CTAText", fontName="Helvetica-Bold", fontSize=14,
        textColor=WHITE, alignment=TA_CENTER, leading=18
    ))
    styles.add(ParagraphStyle(
        "CTASubtext", fontName="Helvetica", fontSize=10,
        textColor=WHITE, alignment=TA_CENTER, leading=14
    ))
    return styles


def dot():
    return '<font color="#FF6B35">\u25cf</font>'


def feature(title, desc, styles):
    return KeepTogether([
        Paragraph(f'{dot()}  {title}', styles["FeatureTitle"]),
        Paragraph(desc, styles["FeatureDesc"]),
        Spacer(1, 6),
    ])


def build_pdf():
    styles = build_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    story = []

    # Header with logo
    logo = Image(LOGO_PATH, width=48 * mm, height=25.4 * mm)
    logo.hAlign = "LEFT"
    story.append(logo)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Family AI Safety Platform", styles["BhapiTitle"]))
    story.append(Paragraph(
        "Protect your family. Empower your school. Monitor AI usage with confidence.",
        styles["BhapiSubtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=2.5, color=ORANGE, spaceAfter=12, spaceBefore=0))

    # Real-Time Monitoring
    story.append(Paragraph("Real-Time AI Monitoring", styles["SectionHead"]))
    for t, d in [
        ("10-Platform Coverage",
         "Monitor conversations across ChatGPT, Gemini, Copilot, Claude, Grok, Character.AI, Replika, Pi, Perplexity, and Poe \u2014 all from one dashboard."),
        ("Browser Extension",
         "Lightweight Manifest V3 extension for Chrome, Firefox, and Safari. Captures AI interactions in real time without slowing down browsing."),
        ("Conversation Summaries",
         "AI-generated summaries of your child\u2019s conversations so parents can stay informed without reading every message."),
        ("Activity Dashboard",
         "See usage trends, session frequency, and platform preferences at a glance with intuitive charts and timelines."),
    ]:
        story.append(feature(t, d, styles))

    # Safety & Risk
    story.append(Paragraph("Safety & Risk Intelligence", styles["SectionHead"]))
    for t, d in [
        ("14-Category Risk Taxonomy",
         "Classifies content across 14 risk categories including violence, self-harm, sexual content, hate speech, and more."),
        ("AI Safety Scores (0\u2013100)",
         "Every conversation receives a safety score. Scores below thresholds trigger automatic alerts to parents or administrators."),
        ("PII Detection",
         "Automatically detects when children share personal information like addresses, phone numbers, or school names with AI chatbots."),
        ("Deepfake Detection",
         "Integrated with Hive and Sensity APIs to detect AI-generated images and deepfake content in conversations."),
        ("Emotional Dependency Detection",
         "Identifies patterns suggesting unhealthy emotional attachment to AI companions like Character.AI or Replika."),
        ("Academic Integrity Monitoring",
         "Flags potential misuse of AI for homework, essays, or exams with configurable sensitivity levels."),
    ]:
        story.append(feature(t, d, styles))

    # Alerts & Controls
    story.append(Paragraph("Alerts & Parental Controls", styles["SectionHead"]))
    for t, d in [
        ("Instant Alerts",
         "Email, SMS, and in-app notifications when risky content is detected. Configurable severity thresholds and digest batching."),
        ("Content Blocking",
         "Block specific AI platforms or sessions in real time. Parent approval flow lets kids request access to blocked content."),
        ("Time Budgets & Bedtime Mode",
         "Set daily AI usage limits per child. Bedtime mode automatically restricts access during sleeping hours."),
        ("Panic Button",
         "Children can instantly alert a parent or guardian if they encounter something distressing during an AI conversation."),
        ("Emergency Contacts",
         "Designate trusted adults who receive alerts when the primary parent is unavailable."),
    ]:
        story.append(feature(t, d, styles))

    # Family Features
    story.append(Paragraph("Family Features", styles["SectionHead"]))
    for t, d in [
        ("Family Agreements",
         "Create and manage household AI usage agreements that children acknowledge before using AI platforms."),
        ("Sibling Privacy",
         "Each child\u2019s data is isolated \u2014 siblings cannot see each other\u2019s activity, and parents control visibility per member."),
        ("Rewards System",
         "Encourage safe AI usage with a built-in rewards system. Recognize responsible behavior and set positive incentives."),
        ("Weekly Reports",
         "Automated weekly digest emails summarizing each child\u2019s AI activity, risk events, and usage trends."),
        ("Child Dashboard",
         "Age-appropriate dashboard where children can view their own safety scores and understand responsible AI use."),
    ]:
        story.append(feature(t, d, styles))

    # School & Organization
    story.append(Paragraph("School & Organization Management", styles["SectionHead"]))
    for t, d in [
        ("Class & Group Management",
         "Organize students into classes, clubs, or groups. Assign monitors, set policies per group, and manage rosters."),
        ("SIS Integration (Clever & ClassLink)",
         "Automatic roster sync with your school\u2019s Student Information System. Supports Clever and ClassLink OneRoster."),
        ("SSO (Google Workspace & Entra)",
         "Single sign-on for staff and students via Google Workspace or Microsoft Entra ID. Directory sync and auto-provisioning."),
        ("Safeguarding Reports",
         "Generate detailed safeguarding reports for school administrators, DSLs, and regulatory bodies."),
        ("Per-Seat Billing",
         "School and club plans use transparent per-seat pricing. Add or remove students as enrollment changes."),
    ]:
        story.append(feature(t, d, styles))

    # Compliance
    story.append(Paragraph("Compliance & Privacy", styles["SectionHead"]))
    for t, d in [
        ("COPPA Compliant",
         "Built from the ground up for children\u2019s privacy. Parental consent enforcement, data minimization, and COPPA certification readiness."),
        ("GDPR & LGPD Ready",
         "Full data rights support: export, deletion, and access requests. Cookie consent and data residency controls."),
        ("EU AI Act Transparency",
         "Automated transparency logging, human review workflows, and appeals process to meet EU AI Act requirements."),
        ("Content Encryption",
         "All captured conversation excerpts are encrypted at rest with automatic TTL-based cleanup."),
        ("Age Verification (Yoti)",
         "Integrated age verification via Yoti to ensure appropriate protections for different age groups."),
    ]:
        story.append(feature(t, d, styles))

    # AI Spend Tracking
    story.append(Paragraph("AI Spend Tracking & Billing", styles["SectionHead"]))
    for t, d in [
        ("LLM Spend Monitoring",
         "Track your family\u2019s or school\u2019s AI spending across OpenAI, Anthropic, Google, Microsoft, and xAI (Grok)."),
        ("API Key Revocation",
         "Instantly revoke compromised API keys from the dashboard. Protect against unauthorized AI spending."),
        ("Vendor Risk Scoring",
         "Assess and compare the safety posture of AI vendors your organization uses."),
        ("Flexible Plans",
         "Family ($9.99/mo), School (per-seat), and Enterprise tiers. All plans include a 14-day free trial."),
    ]:
        story.append(feature(t, d, styles))

    # Global Accessibility
    story.append(Paragraph("Global Accessibility", styles["SectionHead"]))
    for t, d in [
        ("6 Languages",
         "Full interface localization in English, French, Spanish, German, Portuguese (Brazil), and Italian."),
        ("WCAG 2.1 AA Accessible",
         "Designed for accessibility with proper contrast ratios, keyboard navigation, and screen reader support."),
        ("AI Literacy Modules",
         "Built-in educational content with quizzes and assessments to help children understand AI responsibly."),
    ]:
        story.append(feature(t, d, styles))

    story.append(Spacer(1, 10 * mm))

    # CTA banner
    cta_data = [
        [Paragraph("Start protecting your family today", styles["CTAText"])],
        [Paragraph("Visit bhapi.ai  \u2022  14-day free trial  \u2022  No credit card required", styles["CTASubtext"])],
    ]
    cta_table = Table(cta_data, colWidths=[doc.width])
    cta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cta_table)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "\u00a9 2026 Bhapi  \u2022  bhapi.ai  \u2022  AI Safety for Families & Schools",
        styles["Footer"]
    ))

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(WIDTH / 2, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
