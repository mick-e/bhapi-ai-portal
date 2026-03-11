"""Parent education content about deepfakes and synthetic media.

This module provides guidance resources that are served publicly to
help parents understand, prevent, and respond to deepfake content.
"""

from __future__ import annotations

DEEPFAKE_GUIDANCE: dict = {
    "what_is_deepfake": (
        "A deepfake is AI-generated fake media — images, videos, or audio "
        "that look and sound real but were created or manipulated using "
        "artificial intelligence. These can be used to put someone's face "
        "on another person's body, create fake nude images, or clone "
        "someone's voice to impersonate them."
    ),
    "reporting_resources": [
        {
            "name": "NCMEC CyberTipline",
            "url": "https://report.cybertip.org",
            "description": (
                "Report child sexual exploitation material, including "
                "AI-generated images of minors."
            ),
        },
        {
            "name": "FBI IC3",
            "url": "https://www.ic3.gov",
            "description": (
                "Report internet crimes including sextortion and "
                "deepfake-related fraud."
            ),
        },
        {
            "name": "TAKE IT DOWN",
            "url": "https://takeitdown.ncmec.org",
            "description": (
                "Free service by NCMEC that helps remove intimate images "
                "of minors from the internet."
            ),
        },
    ],
    "parent_actions": [
        "Stay calm and reassure your child",
        "Document the content (screenshot if safe to do so)",
        "Report to the platform",
        "Report to NCMEC CyberTipline if it involves a minor",
        "Consider contacting local law enforcement",
    ],
    "prevention_tips": [
        "Discuss with your child what deepfakes are",
        "Limit sharing of personal photos online",
        "Teach critical evaluation of media",
        "Set up privacy settings on social media accounts",
        "Monitor AI tool usage for suspicious patterns",
    ],
}


async def get_deepfake_guidance() -> dict:
    """Return parent-facing deepfake education content."""
    return DEEPFAKE_GUIDANCE
