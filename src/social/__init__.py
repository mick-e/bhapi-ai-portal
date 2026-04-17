"""Social features — feed, posts, comments, likes, profiles, follows.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

# Public interface for cross-module access
from .graph_analysis import analyze_contacts, detect_age_inappropriate_pattern, detect_isolation, map_influence
from .models import SocialPost

from src.social.service import (
    accept_follow,
    add_comment,
    create_post,
    create_profile,
    delete_post,
    extract_hashtags,
    follow_user,
    get_feed,
    get_post,
    get_profile,
    get_profile_by_id,
    get_trending_hashtags,
    like_post,
    list_comments,
    list_followers,
    list_following,
    list_posts,
    search_profiles,
    unfollow_user,
    unlike_post,
    update_profile,
)

__all__ = [
    "accept_follow",
    "add_comment",
    "create_post",
    "create_profile",
    "delete_post",
    "extract_hashtags",
    "follow_user",
    "get_feed",
    "get_post",
    "get_profile",
    "get_profile_by_id",
    "get_trending_hashtags",
    "like_post",
    "list_comments",
    "list_followers",
    "list_following",
    "list_posts",
    "search_profiles",
    "unfollow_user",
    "unlike_post",
    "update_profile",
    "analyze_contacts",
    "detect_age_inappropriate_pattern",
    "detect_isolation",
    "map_influence",
    "SocialPost",
]
