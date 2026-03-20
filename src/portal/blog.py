"""Blog and SEO content management."""

import structlog

logger = structlog.get_logger()

BLOG_POSTS = [
    {
        "id": "ai-safety-guide-parents",
        "title": "The Parent's Guide to AI Safety in 2026",
        "slug": "ai-safety-guide-parents",
        "excerpt": (
            "Everything parents need to know about keeping their children"
            " safe while using AI tools like ChatGPT, Gemini, and Claude."
        ),
        "category": "guides",
        "author": "Bhapi Team",
        "published_at": "2026-03-01T00:00:00Z",
        "reading_time_minutes": 8,
        "tags": ["parents", "safety", "guide"],
        "content": (
            "AI tools are becoming an integral part of how children learn"
            " and create. As a parent, you want to encourage exploration"
            " while ensuring safety. This guide covers the key risks,"
            " practical safety measures, and how monitoring tools like"
            " Bhapi can help you stay informed without being intrusive."
        ),
    },
    {
        "id": "coppa-compliance-schools",
        "title": "COPPA Compliance for Schools Using AI Tools",
        "slug": "coppa-compliance-schools",
        "excerpt": (
            "How schools can meet COPPA requirements while enabling"
            " AI-powered learning."
        ),
        "category": "compliance",
        "author": "Bhapi Team",
        "published_at": "2026-02-15T00:00:00Z",
        "reading_time_minutes": 12,
        "tags": ["schools", "coppa", "compliance"],
        "content": (
            "The Children's Online Privacy Protection Act (COPPA) imposes"
            " strict requirements on operators of websites and online"
            " services directed at children under 13. With the rise of AI"
            " in education, schools face new compliance challenges."
            " Here's how to navigate them."
        ),
    },
    {
        "id": "deepfake-detection-guide",
        "title": "Understanding AI Deepfakes: A Safety Guide",
        "slug": "deepfake-detection-guide",
        "excerpt": (
            "How to identify and respond to AI-generated deepfake"
            " content targeting young people."
        ),
        "category": "safety",
        "author": "Bhapi Team",
        "published_at": "2026-02-01T00:00:00Z",
        "reading_time_minutes": 6,
        "tags": ["deepfakes", "safety", "detection"],
        "content": (
            "Deepfake technology has made it increasingly easy to generate"
            " realistic but fake images, audio, and video. Young people"
            " are particularly vulnerable. This guide explains what"
            " deepfakes are, how to spot them, and what to do if your"
            " child encounters one."
        ),
    },
    {
        "id": "ai-in-classroom",
        "title": "How Teachers Can Safely Integrate AI in the Classroom",
        "slug": "ai-in-classroom",
        "excerpt": (
            "Practical strategies for educators to leverage AI while"
            " maintaining academic integrity."
        ),
        "category": "education",
        "author": "Bhapi Team",
        "published_at": "2026-01-15T00:00:00Z",
        "reading_time_minutes": 10,
        "tags": ["teachers", "education", "classroom"],
        "content": (
            "AI tools can transform education, but they also present"
            " challenges around academic integrity, privacy, and safety."
            " This guide offers practical strategies for teachers who want"
            " to integrate AI responsibly."
        ),
    },
    {
        "id": "enterprise-ai-governance",
        "title": "Enterprise AI Governance: Beyond the Hype",
        "slug": "enterprise-ai-governance",
        "excerpt": (
            "Why organisations need an AI governance framework"
            " and how to build one."
        ),
        "category": "enterprise",
        "author": "Bhapi Team",
        "published_at": "2026-01-01T00:00:00Z",
        "reading_time_minutes": 15,
        "tags": ["enterprise", "governance", "policy"],
        "content": (
            "As AI adoption accelerates across industries, organisations"
            " face growing pressure to govern AI usage responsibly. This"
            " article explores the key components of an effective AI"
            " governance framework."
        ),
    },
]


def get_blog_posts(category: str | None = None, tag: str | None = None) -> list[dict]:
    """Get blog posts with optional filters."""
    posts = BLOG_POSTS
    if category:
        posts = [p for p in posts if p["category"] == category]
    if tag:
        posts = [p for p in posts if tag in p["tags"]]
    return posts


def get_blog_post(slug: str) -> dict | None:
    """Get a single blog post by slug."""
    return next((p for p in BLOG_POSTS if p["slug"] == slug), None)


def get_blog_categories() -> list[str]:
    """Get unique categories."""
    return sorted(set(p["category"] for p in BLOG_POSTS))
