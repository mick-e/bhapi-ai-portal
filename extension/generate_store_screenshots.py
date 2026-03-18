"""Generate Chrome Web Store screenshots (1280x800) for Bhapi AI Safety Monitor."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(__file__), "store-screenshots")
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 800

# Brand colors
DARK_BG = (26, 26, 46)       # #1a1a2e
DARK_PANEL = (22, 33, 62)    # #16213e
RED_ACCENT = (233, 69, 96)   # #e94560
GREEN = (40, 167, 69)        # #28a745
YELLOW = (255, 193, 7)       # #ffc107
WHITE = (255, 255, 255)
LIGHT_BG = (248, 249, 250)   # #f8f9fa
GRAY = (108, 117, 125)       # #6c757d
LIGHT_GRAY = (206, 212, 218)
CARD_BG = (255, 255, 255)
ORANGE = (255, 107, 53)      # #FF6B35 (bhapi brand)
TEAL = (13, 148, 136)        # #0D9488


def get_font(size, bold=False):
    """Try system fonts, fall back to default."""
    names = ["arialbd.ttf", "Arial Bold.ttf"] if bold else ["arial.ttf", "Arial.ttf"]
    for name in names:
        for base in ["C:/Windows/Fonts/", "/usr/share/fonts/truetype/", "/System/Library/Fonts/"]:
            path = os.path.join(base, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded_rect(draw, xy, radius, fill, outline=None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_status_dot(draw, x, y, color, r=6):
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


# ======================================================================
# Screenshot 1: Extension popup connected on ChatGPT page
# ======================================================================
def screenshot_1_popup_connected():
    img = Image.new("RGB", (W, H), LIGHT_BG)
    draw = ImageDraw.Draw(img)
    f_title = get_font(32, bold=True)
    f_heading = get_font(20, bold=True)
    f_body = get_font(16)
    f_small = get_font(13)
    f_label = get_font(12, bold=True)
    f_badge = get_font(11, bold=True)

    # Simulated browser chrome bar at top
    draw.rectangle((0, 0, W, 52), fill=(55, 55, 70))
    draw.rounded_rectangle((200, 10, 900, 42), radius=16, fill=(70, 70, 90))
    draw.text((220, 15), "chatgpt.com", fill=(180, 180, 200), font=f_body)

    # Simulated ChatGPT page content (blurred/dimmed)
    draw.rectangle((0, 52, W, H), fill=(245, 245, 248))
    draw.text((80, 120), "ChatGPT", fill=(180, 180, 190), font=get_font(40, bold=True))
    draw.text((80, 175), "How can I help you today?", fill=(200, 200, 210), font=get_font(22))

    # Draw some placeholder chat bubbles (dimmed)
    for i, (txt, is_user) in enumerate([
        ("Can you help me with my homework?", True),
        ("Of course! What subject are you working on?", False),
        ("Math - I need help with fractions", True),
    ]):
        y_pos = 240 + i * 70
        x_pos = 600 if is_user else 80
        color = (220, 225, 235) if is_user else (230, 230, 240)
        rounded_rect(draw, (x_pos, y_pos, x_pos + 500, y_pos + 50), 12, color)
        draw.text((x_pos + 16, y_pos + 15), txt, fill=(170, 170, 180), font=f_body)

    # Extension popup overlay (right side)
    popup_x, popup_y = 820, 60
    popup_w, popup_h = 380, 440

    # Popup shadow
    rounded_rect(draw, (popup_x + 4, popup_y + 4, popup_x + popup_w + 4, popup_y + popup_h + 4), 12, (0, 0, 0, 40))
    # Popup body
    rounded_rect(draw, (popup_x, popup_y, popup_x + popup_w, popup_y + popup_h), 12, CARD_BG, outline=LIGHT_GRAY)

    # Popup header (dark gradient)
    rounded_rect(draw, (popup_x, popup_y, popup_x + popup_w, popup_y + 60), 12, DARK_BG)
    draw.rectangle((popup_x, popup_y + 30, popup_x + popup_w, popup_y + 60), fill=DARK_BG)

    # Header icon
    rounded_rect(draw, (popup_x + 16, popup_y + 14, popup_x + 48, popup_y + 46), 8, RED_ACCENT)
    draw.text((popup_x + 25, popup_y + 17), "B", fill=WHITE, font=f_heading)

    draw.text((popup_x + 58, popup_y + 15), "Bhapi AI Safety Monitor", fill=WHITE, font=f_label)
    draw.text((popup_x + 58, popup_y + 33), "v1.0.0", fill=(150, 150, 170), font=f_small)

    # Status bar
    status_y = popup_y + 68
    draw.line((popup_x + 12, status_y + 28, popup_x + popup_w - 12, status_y + 28), fill=LIGHT_GRAY)
    draw_status_dot(draw, popup_x + 28, status_y + 13, GREEN)
    draw.text((popup_x + 44, status_y + 5), "Connected to bhapi.ai", fill=(30, 30, 30), font=f_body)

    # Monitoring section
    mon_y = status_y + 40
    draw.text((popup_x + 20, mon_y), "MONITORING", fill=GRAY, font=f_label)

    # Toggle
    toggle_y = mon_y + 26
    draw.text((popup_x + 20, toggle_y + 2), "Enable monitoring", fill=(30, 30, 30), font=f_body)
    # Toggle ON
    rounded_rect(draw, (popup_x + popup_w - 64, toggle_y, popup_x + popup_w - 20, toggle_y + 24), 12, GREEN)
    draw.ellipse((popup_x + popup_w - 42, toggle_y + 3, popup_x + popup_w - 24, toggle_y + 21), fill=WHITE)

    # Info grid
    info_y = toggle_y + 40
    info_items = [
        ("Group", "Johnson Family"),
        ("Member", "Emma (age 12)"),
        ("Platform", "ChatGPT"),
        ("Last event", "2 seconds ago"),
        ("Queued", "0"),
    ]
    for i, (label, val) in enumerate(info_items):
        y = info_y + i * 24
        draw.text((popup_x + 20, y), label, fill=GRAY, font=f_small)
        draw.text((popup_x + 140, y), val, fill=(30, 30, 30), font=f_small)

    # Buttons
    btn_y = info_y + len(info_items) * 24 + 16
    rounded_rect(draw, (popup_x + 20, btn_y, popup_x + 120, btn_y + 34), 6, (108, 117, 125))
    draw.text((popup_x + 40, btn_y + 8), "Refresh", fill=WHITE, font=f_small)
    rounded_rect(draw, (popup_x + 130, btn_y, popup_x + 260, btn_y + 34), 6, (108, 117, 125))
    draw.text((popup_x + 145, btn_y + 8), "Disconnect", fill=WHITE, font=f_small)

    # Title callout at bottom-left
    rounded_rect(draw, (40, H - 130, 740, H - 30), 16, DARK_BG)
    draw.text((70, H - 115), "Real-time AI monitoring for your family", fill=WHITE, font=f_title)
    draw.text((70, H - 75), "See when and how your children use ChatGPT, Claude, Gemini, and 7 more platforms", fill=(180, 180, 200), font=f_body)

    img.save(os.path.join(OUT, "01-popup-connected.png"), "PNG")
    print("Generated: 01-popup-connected.png")


# ======================================================================
# Screenshot 2: Dashboard overview
# ======================================================================
def screenshot_2_dashboard():
    img = Image.new("RGB", (W, H), (245, 247, 250))
    draw = ImageDraw.Draw(img)
    f_title = get_font(28, bold=True)
    f_heading = get_font(18, bold=True)
    f_body = get_font(15)
    f_small = get_font(12)
    f_label = get_font(11, bold=True)
    f_stat = get_font(36, bold=True)

    # Sidebar
    sidebar_w = 240
    draw.rectangle((0, 0, sidebar_w, H), fill=DARK_BG)

    # Logo in sidebar
    rounded_rect(draw, (20, 20, 52, 52), 8, RED_ACCENT)
    draw.text((28, 24), "B", fill=WHITE, font=f_heading)
    draw.text((62, 28), "bhapi.ai", fill=WHITE, font=f_heading)

    # Nav items
    nav_items = [
        ("Dashboard", True),
        ("Activity", False),
        ("Alerts", False),
        ("Members", False),
        ("Time Budgets", False),
        ("Blocking Rules", False),
        ("Reports", False),
        ("AI Literacy", False),
        ("Settings", False),
    ]
    for i, (label, active) in enumerate(nav_items):
        y = 90 + i * 40
        if active:
            rounded_rect(draw, (8, y - 4, sidebar_w - 8, y + 28), 8, (233, 69, 96, 40))
            draw.rectangle((8, y - 4, sidebar_w - 8, y + 28), fill=(60, 30, 50))
            draw.text((24, y), label, fill=ORANGE, font=f_body)
        else:
            draw.text((24, y), label, fill=(140, 140, 160), font=f_body)

    # Main content area
    cx = sidebar_w + 30
    cy = 20

    draw.text((cx, cy), "Family Dashboard", fill=DARK_BG, font=f_title)
    draw.text((cx, cy + 36), "Johnson Family  \u2022  4 members  \u2022  Last activity: 2 min ago", fill=GRAY, font=f_body)

    # Stat cards row
    stat_y = cy + 80
    stats = [
        ("Safety Score", "92", GREEN, "/100"),
        ("Sessions Today", "7", TEAL, "across 3 platforms"),
        ("Active Alerts", "1", YELLOW, "flagged for review"),
        ("AI Time Today", "47m", DARK_BG, "of 2h budget"),
    ]
    card_w = (W - sidebar_w - 90) // 4
    for i, (label, value, color, sub) in enumerate(stats):
        x = cx + i * (card_w + 10)
        rounded_rect(draw, (x, stat_y, x + card_w, stat_y + 120), 12, CARD_BG)
        draw.text((x + 16, stat_y + 12), label, fill=GRAY, font=f_label)
        draw.text((x + 16, stat_y + 34), value, fill=color, font=f_stat)
        draw.text((x + 16, stat_y + 84), sub, fill=GRAY, font=f_small)

    # Recent activity section
    act_y = stat_y + 150
    rounded_rect(draw, (cx, act_y, W - 30, act_y + 320), 12, CARD_BG)
    draw.text((cx + 20, act_y + 16), "Recent Activity", fill=DARK_BG, font=f_heading)

    activities = [
        ("Emma", "ChatGPT", "Homework help session", "2 min ago", "12m", GREEN),
        ("Emma", "Character.AI", "Conversation", "1 hour ago", "8m", YELLOW),
        ("Jake", "Google Gemini", "Research for science project", "2 hours ago", "15m", GREEN),
        ("Emma", "Claude", "Writing assistance", "3 hours ago", "5m", GREEN),
        ("Jake", "ChatGPT", "Math problem solving", "Yesterday", "20m", GREEN),
    ]

    # Table header
    header_y = act_y + 50
    cols = [cx + 20, cx + 110, cx + 250, cx + 470, cx + 620, cx + 720]
    headers = ["Member", "Platform", "Activity", "When", "Duration", "Safety"]
    for col_x, h in zip(cols, headers):
        draw.text((col_x, header_y), h, fill=GRAY, font=f_label)
    draw.line((cx + 12, header_y + 22, W - 42, header_y + 22), fill=LIGHT_GRAY)

    for i, (member, platform, activity, when, dur, safety_color) in enumerate(activities):
        y = header_y + 32 + i * 46
        draw.text((cols[0], y), member, fill=DARK_BG, font=f_body)
        # Platform badge
        rounded_rect(draw, (cols[1], y - 2, cols[1] + 110, y + 20), 10, (235, 240, 250))
        draw.text((cols[1] + 8, y), platform, fill=DARK_PANEL, font=f_small)
        draw.text((cols[2], y), activity, fill=(80, 80, 100), font=f_body)
        draw.text((cols[3], y), when, fill=GRAY, font=f_small)
        draw.text((cols[4], y), dur, fill=DARK_BG, font=f_body)
        draw_status_dot(draw, cols[5] + 6, y + 8, safety_color, 7)

        if i < len(activities) - 1:
            draw.line((cx + 20, y + 34, W - 42, y + 34), fill=(240, 242, 245))

    img.save(os.path.join(OUT, "02-dashboard.png"), "PNG")
    print("Generated: 02-dashboard.png")


# ======================================================================
# Screenshot 3: Safety alerts
# ======================================================================
def screenshot_3_alerts():
    img = Image.new("RGB", (W, H), (245, 247, 250))
    draw = ImageDraw.Draw(img)
    f_title = get_font(28, bold=True)
    f_heading = get_font(18, bold=True)
    f_body = get_font(15)
    f_small = get_font(12)
    f_label = get_font(11, bold=True)

    # Sidebar (same as dashboard but Alerts active)
    sidebar_w = 240
    draw.rectangle((0, 0, sidebar_w, H), fill=DARK_BG)
    rounded_rect(draw, (20, 20, 52, 52), 8, RED_ACCENT)
    draw.text((28, 24), "B", fill=WHITE, font=f_heading)
    draw.text((62, 28), "bhapi.ai", fill=WHITE, font=f_heading)

    nav_items = ["Dashboard", "Activity", "Alerts", "Members", "Time Budgets", "Blocking Rules", "Reports"]
    for i, label in enumerate(nav_items):
        y = 90 + i * 40
        if label == "Alerts":
            draw.rectangle((8, y - 4, sidebar_w - 8, y + 28), fill=(60, 30, 50))
            draw.text((24, y), label, fill=ORANGE, font=f_body)
            # Alert count badge
            rounded_rect(draw, (sidebar_w - 50, y - 1, sidebar_w - 18, y + 19), 10, RED_ACCENT)
            draw.text((sidebar_w - 43, y + 1), "3", fill=WHITE, font=f_small)
        else:
            draw.text((24, y), label, fill=(140, 140, 160), font=f_body)

    # Main content
    cx = sidebar_w + 30
    draw.text((cx, 20), "Safety Alerts", fill=DARK_BG, font=f_title)
    draw.text((cx, 56), "3 active alerts requiring your attention", fill=GRAY, font=f_body)

    alerts = [
        ("High", RED_ACCENT, "Unusual session length detected",
         "Emma spent 45 minutes on Character.AI \u2014 exceeds normal pattern by 3x. Review conversation summary.",
         "10 minutes ago", "Emma \u2022 Character.AI"),
        ("Medium", YELLOW, "New platform detected",
         "Jake accessed Replika for the first time. Consider reviewing this platform's safety rating before allowing continued use.",
         "2 hours ago", "Jake \u2022 Replika"),
        ("Low", TEAL, "Time budget approaching limit",
         "Emma has used 45 of 60 minutes of her daily AI time budget. She will be notified at the 50-minute mark.",
         "3 hours ago", "Emma \u2022 All platforms"),
    ]

    alert_y = 100
    for sev, color, title, desc, when, source in alerts:
        card_h = 130
        rounded_rect(draw, (cx, alert_y, W - 30, alert_y + card_h), 12, CARD_BG)
        # Severity stripe
        draw.rectangle((cx, alert_y + 10, cx + 5, alert_y + card_h - 10), fill=color)

        # Severity badge
        badge_w = 70 if sev == "Medium" else 50
        rounded_rect(draw, (cx + 20, alert_y + 16, cx + 20 + badge_w, alert_y + 36), 10, (*color, 40))
        draw.text((cx + 28, alert_y + 19), sev, fill=color, font=f_label)

        draw.text((cx + 20 + badge_w + 12, alert_y + 17), title, fill=DARK_BG, font=f_heading)
        draw.text((cx + 20, alert_y + 48), desc[:110], fill=(80, 80, 100), font=f_body)
        if len(desc) > 110:
            draw.text((cx + 20, alert_y + 68), desc[110:], fill=(80, 80, 100), font=f_body)

        draw.text((cx + 20, alert_y + card_h - 30), when, fill=GRAY, font=f_small)
        draw.text((cx + 200, alert_y + card_h - 30), source, fill=GRAY, font=f_small)

        # Action buttons
        rounded_rect(draw, (W - 250, alert_y + card_h - 38, W - 160, alert_y + card_h - 12), 6, RED_ACCENT)
        draw.text((W - 240, alert_y + card_h - 34), "Review", fill=WHITE, font=f_small)
        rounded_rect(draw, (W - 150, alert_y + card_h - 38, W - 50, alert_y + card_h - 12), 6, (108, 117, 125))
        draw.text((W - 140, alert_y + card_h - 34), "Dismiss", fill=WHITE, font=f_small)

        alert_y += card_h + 16

    img.save(os.path.join(OUT, "03-safety-alerts.png"), "PNG")
    print("Generated: 03-safety-alerts.png")


# ======================================================================
# Screenshot 4: 10 Platforms supported (marketing)
# ======================================================================
def screenshot_4_platforms():
    img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)
    f_huge = get_font(42, bold=True)
    f_title = get_font(28, bold=True)
    f_body = get_font(18)
    f_heading = get_font(20, bold=True)
    f_small = get_font(14)

    # Title section
    draw.text((W // 2 - 320, 40), "Monitors 10 AI Platforms", fill=WHITE, font=f_huge)
    draw.text((W // 2 - 260, 95), "Real-time safety monitoring across every major AI platform", fill=(160, 160, 190), font=f_body)

    # Platform cards in 2 rows of 5
    platforms = [
        ("ChatGPT", "OpenAI", (16, 163, 127)),
        ("Gemini", "Google", (66, 133, 244)),
        ("Copilot", "Microsoft", (0, 120, 212)),
        ("Claude", "Anthropic", (204, 147, 89)),
        ("Grok", "xAI", (100, 100, 120)),
        ("Character.AI", "Character", (255, 198, 41)),
        ("Replika", "Luka Inc", (255, 111, 97)),
        ("Pi", "Inflection", (100, 200, 180)),
        ("Perplexity", "Perplexity AI", (32, 178, 170)),
        ("Poe", "Quora", (99, 102, 241)),
    ]

    card_w, card_h = 210, 140
    gap = 20
    start_x = (W - (5 * card_w + 4 * gap)) // 2
    start_y = 160

    for i, (name, company, color) in enumerate(platforms):
        row = i // 5
        col = i % 5
        x = start_x + col * (card_w + gap)
        y = start_y + row * (card_h + gap)

        rounded_rect(draw, (x, y, x + card_w, y + card_h), 12, (35, 40, 65))

        # Color accent bar
        draw.rectangle((x + 12, y + 12, x + 52, y + 52), fill=color)
        rounded_rect(draw, (x + 12, y + 12, x + 52, y + 52), 8, color)

        # Initial letter
        draw.text((x + 22, y + 15), name[0], fill=WHITE, font=f_title)

        # Name
        draw.text((x + 64, y + 16), name, fill=WHITE, font=f_heading)
        draw.text((x + 64, y + 42), company, fill=(140, 140, 160), font=f_small)

        # Status
        draw_status_dot(draw, x + 24, y + card_h - 24, GREEN, 5)
        draw.text((x + 36, y + card_h - 32), "Monitoring", fill=(100, 200, 120), font=f_small)

    # Bottom features bar
    features_y = start_y + 2 * (card_h + gap) + 40
    features = [
        "Session Tracking",
        "Time Budgets",
        "Safety Alerts",
        "Platform Blocking",
        "Bedtime Mode",
        "Spend Tracking",
    ]

    feat_start_x = (W - (6 * 170 + 5 * 15)) // 2
    for i, feat_name in enumerate(features):
        x = feat_start_x + i * 185
        rounded_rect(draw, (x, features_y, x + 170, features_y + 50), 25, (50, 55, 80))
        draw.text((x + 16, features_y + 15), f"\u2713  {feat_name}", fill=(180, 200, 255), font=f_small)

    # Bottom tagline
    draw.text((W // 2 - 200, H - 80), "Privacy-first  \u2022  COPPA compliant  \u2022  GDPR ready", fill=(120, 120, 150), font=f_body)
    draw.text((W // 2 - 60, H - 45), "bhapi.ai", fill=ORANGE, font=f_title)

    img.save(os.path.join(OUT, "04-platforms.png"), "PNG")
    print("Generated: 04-platforms.png")


# ======================================================================
# Screenshot 5: Promotional tile (440x280 — optional but recommended)
# ======================================================================
def screenshot_5_promo_tile():
    pw, ph = 440, 280
    img = Image.new("RGB", (pw, ph), DARK_BG)
    draw = ImageDraw.Draw(img)
    f_title = get_font(22, bold=True)
    f_sub = get_font(13)
    f_small = get_font(11)

    # Bhapi logo area
    rounded_rect(draw, (20, 20, 52, 52), 8, RED_ACCENT)
    draw.text((28, 24), "B", fill=WHITE, font=get_font(18, bold=True))
    draw.text((60, 26), "Bhapi", fill=WHITE, font=f_title)

    # Main text
    draw.text((20, 80), "AI Safety Monitor", fill=WHITE, font=get_font(28, bold=True))
    draw.text((20, 118), "for Families & Schools", fill=ORANGE, font=f_title)

    draw.text((20, 160), "Monitor 10 AI platforms including", fill=(160, 160, 190), font=f_sub)
    draw.text((20, 180), "ChatGPT, Claude, Gemini, Copilot & more", fill=(160, 160, 190), font=f_sub)

    # Bottom bar
    draw.text((20, ph - 40), "14-day free trial  \u2022  $9.99/mo  \u2022  bhapi.ai", fill=GRAY, font=f_small)

    # Decorative dots (platform colors)
    colors = [(16, 163, 127), (66, 133, 244), (0, 120, 212), (204, 147, 89), (255, 198, 41)]
    for i, c in enumerate(colors):
        draw.ellipse((pw - 120 + i * 22, 30, pw - 108 + i * 22, 42), fill=c)

    img.save(os.path.join(OUT, "05-promo-tile-440x280.png"), "PNG")
    print("Generated: 05-promo-tile-440x280.png")


if __name__ == "__main__":
    screenshot_1_popup_connected()
    screenshot_2_dashboard()
    screenshot_3_alerts()
    screenshot_4_platforms()
    screenshot_5_promo_tile()
    print(f"\nAll screenshots saved to: {OUT}")
