"""Generate combined Bhapi Mobile + Back-Office Portal features PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_CENTER
import os

ORANGE = HexColor("#FF6B35")
TEAL = HexColor("#0D9488")
DARK = HexColor("#1F2937")
GRAY = HexColor("#6B7280")
LIGHT_BG = HexColor("#FFF7F3")
WHITE = white

LOGO_PATH = os.path.join(os.path.dirname(__file__), "portal", "public", "logo.png")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Bhapi_App_and_Platform_Features.pdf")

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
        "PartTitle", fontName="Helvetica-Bold", fontSize=22,
        textColor=WHITE, spaceAfter=0, leading=28, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "PartSubtitle", fontName="Helvetica", fontSize=11,
        textColor=WHITE, spaceAfter=0, leading=15, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "SectionHead", fontName="Helvetica-Bold", fontSize=15,
        textColor=ORANGE, spaceBefore=16, spaceAfter=6, leading=19
    ))
    styles.add(ParagraphStyle(
        "SubSection", fontName="Helvetica-Bold", fontSize=11,
        textColor=TEAL, spaceBefore=8, spaceAfter=4, leading=14
    ))
    styles.add(ParagraphStyle(
        "FeatureTitle", fontName="Helvetica-Bold", fontSize=10,
        textColor=DARK, spaceAfter=1, leading=13
    ))
    styles.add(ParagraphStyle(
        "FeatureDesc", fontName="Helvetica", fontSize=9,
        textColor=GRAY, spaceAfter=0, leading=12
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


def dot(color="#FF6B35"):
    return f'<font color="{color}">\u25cf</font>'


def feat(title, desc, styles):
    return KeepTogether([
        Paragraph(f'{dot()}  {title}', styles["FeatureTitle"]),
        Paragraph(desc, styles["FeatureDesc"]),
        Spacer(1, 5),
    ])


def part_banner(title, subtitle, styles, doc_width):
    data = [
        [Paragraph(title, styles["PartTitle"])],
        [Paragraph(subtitle, styles["PartSubtitle"])],
    ]
    t = Table(data, colWidths=[doc_width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("TOPPADDING", (0, 0), (-1, 0), 16),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def build_pdf():
    styles = build_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    story = []

    # ===== COVER HEADER =====
    logo = Image(LOGO_PATH, width=48 * mm, height=25.4 * mm)
    logo.hAlign = "LEFT"
    story.append(logo)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Bhapi App & Platform", styles["BhapiTitle"]))
    story.append(Paragraph(
        "Complete feature overview \u2014 Mobile App + Back-Office Portal",
        styles["BhapiSubtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=2.5, color=ORANGE, spaceAfter=16, spaceBefore=0))

    # =========================================================
    # PART 1: MOBILE APP
    # =========================================================
    story.append(part_banner(
        "Part 1 \u2014 Bhapi Mobile App",
        "iOS & Android \u2022 Safe social networking for families",
        styles, doc.width
    ))
    story.append(Spacer(1, 4 * mm))

    # --- Authentication & Onboarding ---
    story.append(Paragraph("Authentication & Onboarding", styles["SectionHead"]))
    for t, d in [
        ("Login", "Email/username and password authentication."),
        ("Sign Up", "Multi-step registration collecting basic info, birthday, photo, and password."),
        ("Forgot Password", "Easy recovery with a one-time code (OTP) sent via email or phone."),
        ("Password Reset", "Set a new password after identity verification."),
        ("OTP Verification", "One-time passcodes via email/SMS for secure verification."),
        ("Two-Factor Authentication", "Optional extra security step during login for added protection."),
        ("Welcome Screen", "Smart routing \u2014 detects if you\u2019re logged in or new and sends you to the right place."),
    ]:
        story.append(feat(t, d, styles))

    # --- Feed ---
    story.append(Paragraph("Feed", styles["SectionHead"]))
    for t, d in [
        ("Public Feed", "Infinite-scroll feed of public posts, loading 5 at a time for smooth performance."),
        ("Pull-to-Refresh", "Swipe down to instantly load the latest posts."),
        ("Post Cards", "Rich display of text, photos/videos, hashtags, mentions, and shared content."),
        ("Feed Header", "App logo, profile shortcut, and search button always accessible."),
    ]:
        story.append(feat(t, d, styles))

    # --- Posts ---
    story.append(Paragraph("Posts", styles["SectionHead"]))
    for t, d in [
        ("Create Post", "Write text, tag users, use hashtags, attach photos, or use the camera directly."),
        ("Post Detail", "Full single-post view with all comments and interactions."),
        ("Post Actions", "Like, comment, and share any post."),
        ("Post Options (Yours)", "Edit or delete your own posts."),
        ("Post Options (Others)", "Hide, block the user, or report the post."),
        ("Drafts", "Save unfinished posts to work on later."),
        ("Hashtag Pages", "Tap any hashtag to discover all posts using it."),
    ]:
        story.append(feat(t, d, styles))

    # --- Content Safety ---
    story.append(Paragraph("Content Safety & Moderation", styles["SectionHead"]))
    for t, d in [
        ("Toxicity Detection", "Google\u2019s API scores every post and comment for toxicity. Posts exceeding the configurable threshold (default 0.5) are automatically flagged."),
        ("Configurable Threshold", "Toxicity sensitivity can be adjusted by admins in the back-office settings."),
        ("Multi-Language Support", "Content analysis works across multiple languages."),
        ("Smart Pre-processing", "Removes @mentions and emojis before toxicity analysis for accurate scoring."),
        ("SafeSearch Detection", "Google Cloud Vision checks images for adult content, violence, and more. Scores above 2 block the image."),
        ("Video Content Detection", "Google Video Intelligence scans video frames for inappropriate content \u2014 the worst frame determines the post status."),
        ("Post Status Workflow", "Posts flow through Public, Pending, Blocked, or Draft states based on analysis results."),
        ("Auto-Assignment", "Pending and blocked posts are automatically assigned to the moderator with the lightest workload."),
        ("Comment Analysis", "Every comment is checked for toxicity before publication."),
        ("Post Edit Re-Analysis", "Editing a post triggers a fresh content check \u2014 status may change."),
        ("Report Flow", "Users can easily report content with a reason and message from the app."),
        ("Upload Progress", "Real-time progress indicators for media upload and content analysis."),
        ("Reporter Notification", "Users who reported content are notified once a moderator takes action."),
    ]:
        story.append(feat(t, d, styles))

    # --- Comments ---
    story.append(Paragraph("Comments", styles["SectionHead"]))
    for t, d in [
        ("Threaded Comments", "View all comments on a post organized in threads."),
        ("Post Comment", "Write and submit comments with toxicity pre-check."),
        ("Comment Actions", "Like comments to show appreciation."),
        ("Comment Metadata", "Timestamp and like count displayed for every comment."),
    ]:
        story.append(feat(t, d, styles))

    # --- Messaging ---
    story.append(Paragraph("Messaging", styles["SectionHead"]))
    for t, d in [
        ("Message List", "Inbox with all 1-on-1 and group conversations."),
        ("Pair Chat", "Real-time 1-on-1 messaging via WebSocket."),
        ("Group Chat", "Real-time group messaging with multiple users via WebSocket."),
        ("Message Reactions", "Quick emoji reactions on messages (thumbs up, hearts, etc.)."),
        ("Chat Settings", "Per-conversation configuration options."),
        ("Group Management", "Create groups, manage members, edit group name and photo."),
        ("User Profile Modal", "View chat user\u2019s profile and block/unblock directly from the conversation."),
        ("Active Users", "Real-time online status indicators."),
        ("Message Search", "Search within your chats to find specific messages."),
    ]:
        story.append(feat(t, d, styles))

    # --- Notifications ---
    story.append(Paragraph("Notifications", styles["SectionHead"]))
    for t, d in [
        ("Notification List", "View all alerts with pull-to-refresh for new ones."),
        ("Notification Detail", "Expanded view of each notification with full context."),
        ("Unread Badge", "Tab badge showing your unread notification count."),
    ]:
        story.append(feat(t, d, styles))

    # --- User Profiles ---
    story.append(Paragraph("User Profiles", styles["SectionHead"]))
    for t, d in [
        ("View Profile", "See avatar, bio, post count, followers, and following."),
        ("Profile Tabs", "Switch between list (stack) or grid view of posts (\u201cMemories\u201d)."),
        ("Edit Profile", "Update photo, name, bio, and personal information."),
        ("Profile Not Found", "Clean handling for deleted or non-existent profiles."),
    ]:
        story.append(feat(t, d, styles))

    # --- Social Features ---
    story.append(Paragraph("Social Features", styles["SectionHead"]))
    for t, d in [
        ("Follow / Unfollow", "Follow or unfollow users from profiles and search results."),
        ("Followers / Following", "Lists of all followers and people you follow."),
        ("User Search", "Find people by name or username."),
        ("Block / Unblock", "Block users from settings or chat profiles."),
        ("Report", "Report posts or users with categorized reasons (abusive, self-harm, etc.)."),
    ]:
        story.append(feat(t, d, styles))

    # --- Search & Discovery ---
    story.append(Paragraph("Search & Discovery", styles["SectionHead"]))
    for t, d in [
        ("Search Screen", "Unified search with separate tabs for People and Memories (posts)."),
        ("People Search", "Find users and follow them directly from results."),
        ("Memory Search", "Find posts by keywords with photo previews."),
        ("Suggestions", "\u201cPeople you know\u201d section with up to 10 smart suggestions."),
    ]:
        story.append(feat(t, d, styles))

    # --- Media ---
    story.append(Paragraph("Media", styles["SectionHead"]))
    for t, d in [
        ("Photo Picker", "Select photos from your device\u2019s library."),
        ("Camera", "Take photos directly within the app."),
        ("Media Preview", "Full-screen viewer for photos and videos."),
        ("Media in Posts", "Rich display of photos and videos in feed and post details."),
        ("Secure File Uploads", "Handles media uploads securely with progress tracking."),
    ]:
        story.append(feat(t, d, styles))

    # --- Account & Settings ---
    story.append(Paragraph("Account & Settings", styles["SectionHead"]))
    for t, d in [
        ("Account Screen", "Main profile view with all your posts and actions."),
        ("Settings", "Organized options for contact, security, and privacy."),
        ("Update Email / Phone / Password", "Change your contact details and credentials."),
        ("Two-Factor Authentication", "Enable or disable TFA with code and password verification."),
        ("Sub Accounts", "Create and manage child or linked accounts."),
        ("Blocking", "View and manage your blocked users list."),
        ("Delete Account", "Permanently close your account with confirmation."),
        ("Contacts", "Import and invite friends from your device\u2019s address book."),
    ]:
        story.append(feat(t, d, styles))

    # --- Support ---
    story.append(Paragraph("Support", styles["SectionHead"]))
    story.append(feat("In-App Support Chat", "Direct conversation with support team from within the app.", styles))

    # =========================================================
    # PART 2: BACK-OFFICE PORTAL
    # =========================================================
    story.append(Spacer(1, 6 * mm))
    story.append(part_banner(
        "Part 2 \u2014 Bhapi Back-Office Portal",
        "Web Dashboard \u2022 Administration & Content Moderation",
        styles, doc.width
    ))
    story.append(Spacer(1, 4 * mm))

    # --- Authentication ---
    story.append(Paragraph("Authentication", styles["SectionHead"]))
    for t, d in [
        ("Login", "Email and password authentication for administrators."),
        ("Register", "Organization registration with admin account creation (new or existing user)."),
        ("Forgot Password", "Request password reset code via email."),
        ("Reset Password", "Set new password using verification code."),
    ]:
        story.append(feat(t, d, styles))

    # --- Dashboard ---
    story.append(Paragraph("Dashboard", styles["SectionHead"]))
    story.append(feat("Dashboard", "Landing page after login with organization overview header.", styles))

    # --- Accounts Management ---
    story.append(Paragraph("Accounts Management", styles["SectionHead"]))
    for t, d in [
        ("Accounts List", "View all accounts in the organization with pagination."),
        ("Status Filter", "Filter accounts by All, Active, Inactive, Invited, or Incomplete."),
        ("Search", "Search accounts by name or email."),
        ("Add / Import Accounts", "Add new accounts individually or import in bulk (Admin only)."),
        ("Send Invitation", "Send invite emails to selected accounts."),
        ("Remove Incomplete", "Clean up accounts with incomplete registration."),
        ("Remove from Organization", "Remove selected accounts from the organization."),
        ("Account Detail", "View detailed account information in a modal."),
        ("Sub Accounts", "View sub-account count per user."),
    ]:
        story.append(feat(t, d, styles))

    # --- Organizations Management ---
    story.append(Paragraph("Organizations Management (Admin Only)", styles["SectionHead"]))
    for t, d in [
        ("Organizations List", "View all organizations with pagination."),
        ("Status Filter", "Filter by All, Active, Pending, or Invited."),
        ("Search", "Search organizations by name."),
        ("Add Organization", "Create new organizations via modal."),
        ("Send Invitation", "Invite organizations individually or in bulk."),
        ("Delete Pending", "Remove pending organizations."),
        ("Organization Detail", "Navigate to any organization\u2019s accounts list."),
    ]:
        story.append(feat(t, d, styles))

    # --- Content Moderation ---
    story.append(Paragraph("Content Moderation", styles["SectionHead"]))

    story.append(Paragraph("Published Posts", styles["SubSection"]))
    for t, d in [
        ("Published Posts List", "View all published public posts with pagination."),
        ("Type Filter", "Filter by All, Text, Share, Link, or Media."),
        ("Create Post", "Create new posts on behalf of users via modal (select user, add text/media)."),
        ("View Post", "Preview post content (text, media, user info) in a modal."),
    ]:
        story.append(feat(t, d, styles))

    story.append(Paragraph("Blocked Posts", styles["SubSection"]))
    for t, d in [
        ("Blocked Posts List", "View posts flagged by the content analyzer with pagination."),
        ("Type & Status Filters", "Filter by content type and status (Pending, Blocked)."),
        ("Moderator Filter", "Filter by assigned moderator (Admin only)."),
        ("Review Post", "View post content and take action \u2014 Block or Approve."),
        ("Toxicity Score", "Display content analyzer toxicity score per post."),
    ]:
        story.append(feat(t, d, styles))

    story.append(Paragraph("Reported Posts", styles["SubSection"]))
    for t, d in [
        ("Reported Posts List", "View user-reported posts with pagination."),
        ("Type Filter", "Filter by All, Text, Share, Link, or Media."),
        ("Review Post", "View reported content with report message and issue type."),
        ("Report Details", "Shows reporter message, issue category, and report date."),
    ]:
        story.append(feat(t, d, styles))

    # --- Support Tickets ---
    story.append(Paragraph("Support Tickets", styles["SectionHead"]))
    for t, d in [
        ("Ticket List", "View all support tickets with pagination."),
        ("Status Filter", "Filter by All, Open, Pending, Reopened, Closed, or Solved."),
        ("Live Chat", "Real-time WebSocket chat with support users."),
        ("Open / Close Ticket", "Start conversations on pending tickets and close resolved ones."),
        ("Chat History", "View full message history per ticket."),
        ("Ticket Details", "User name, issue description, assignee, status, and creation date."),
        ("Minimize / Expand", "Collapse and expand the chat window."),
    ]:
        story.append(feat(t, d, styles))

    # --- Settings ---
    story.append(Paragraph("Settings (Admin Only)", styles["SectionHead"]))

    story.append(Paragraph("General Settings", styles["SubSection"]))
    for t, d in [
        ("Content Analyzer", "Configure the accepted toxicity score threshold for automated moderation."),
        ("Invite & Download", "Configure invitation title, message, App Store URL, Google Play URL, and redirect URL."),
    ]:
        story.append(feat(t, d, styles))

    story.append(Paragraph("Email Templates", styles["SubSection"]))
    story.append(feat("Organization Invitation", "Edit email invitation title and content using rich text editor.", styles))

    story.append(Paragraph("Invitation Content", styles["SubSection"]))
    for t, d in [
        ("Invite Organizations", "Edit invitation title and content for organization invites using rich text editor."),
        ("Invite Parents", "Edit invitation title and content for parent invites using rich text editor."),
    ]:
        story.append(feat(t, d, styles))

    # ===== CTA + FOOTER =====
    story.append(Spacer(1, 10 * mm))
    cta_data = [
        [Paragraph("Build safer digital communities with Bhapi", styles["CTAText"])],
        [Paragraph("bhapi.ai  \u2022  Contact us for a demo  \u2022  Available on iOS, Android & Web", styles["CTASubtext"])],
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
        "\u00a9 2026 Bhapi  \u2022  bhapi.ai  \u2022  Safe Social Networking for Families & Organizations",
        styles["Footer"]
    ))

    def add_page_footer(canvas, doc):
        canvas.saveState()
        # Logo on every page top-left
        canvas.drawImage(LOGO_PATH, 20 * mm, HEIGHT - 12 * mm, width=24 * mm, height=12.7 * mm,
                         preserveAspectRatio=True, mask="auto")
        # Page number bottom center
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(WIDTH / 2, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def first_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(WIDTH / 2, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=first_page, onLaterPages=add_page_footer)
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
