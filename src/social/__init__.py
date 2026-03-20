"""Social features — feed, posts, comments, likes, profiles, follows.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

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
    "unfollow_user",
    "unlike_post",
    "update_profile",
]
