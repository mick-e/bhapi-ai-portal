"""Unit tests for social, contacts, moderation, governance, messaging models."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Contacts models
from src.contacts.models import Contact, ContactApproval

# Governance models
from src.governance.models import GovernanceAudit, GovernancePolicy

# Messaging models
from src.messaging.models import (
    Conversation,
    ConversationMember,
    Message,
    MessageMedia,
)

# Moderation models
from src.moderation.models import (
    ContentReport,
    MediaAsset,
    ModerationDecision,
    ModerationQueue,
)

# Social models
from src.social.models import (
    Follow,
    Hashtag,
    PostComment,
    PostHashtag,
    PostLike,
    Profile,
    SocialPost,
)
from tests.conftest import make_test_group


# ─── Helper ─────────────────────────────────────────────────────────
async def _make_user(session):
    """Create a test user via make_test_group and return the owner_id."""
    _, owner_id = await make_test_group(session)
    return owner_id


async def _make_user_and_group(session):
    """Create a test user+group and return (group, owner_id)."""
    return await make_test_group(session)


# ═══════════════════════════════════════════════════════════════════
# Profile tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_profile(test_session):
    user_id = await _make_user(test_session)
    profile = Profile(
        user_id=user_id,
        display_name="Alice",
        age_tier="10-12",
        date_of_birth=date(2014, 5, 15),
    )
    test_session.add(profile)
    await test_session.flush()

    result = await test_session.get(Profile, profile.id)
    assert result is not None
    assert result.display_name == "Alice"
    assert result.visibility == "friends_only"
    assert result.avatar_url is None
    assert result.bio is None


@pytest.mark.asyncio
async def test_profile_user_id_unique(test_session):
    user_id = await _make_user(test_session)
    p1 = Profile(
        user_id=user_id,
        display_name="Alice",
        age_tier="10-12",
        date_of_birth=date(2014, 5, 15),
    )
    test_session.add(p1)
    await test_session.flush()

    p2 = Profile(
        user_id=user_id,
        display_name="Alice Duplicate",
        age_tier="10-12",
        date_of_birth=date(2014, 5, 15),
    )
    test_session.add(p2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_profile_optional_fields(test_session):
    user_id = await _make_user(test_session)
    profile = Profile(
        user_id=user_id,
        display_name="Bob",
        avatar_url="https://example.com/avatar.png",
        bio="Hello world",
        age_tier="13-15",
        date_of_birth=date(2012, 1, 1),
        visibility="public",
    )
    test_session.add(profile)
    await test_session.flush()

    result = await test_session.get(Profile, profile.id)
    assert result.avatar_url == "https://example.com/avatar.png"
    assert result.bio == "Hello world"
    assert result.visibility == "public"


# ═══════════════════════════════════════════════════════════════════
# SocialPost tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_social_post(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(
        author_id=user_id,
        content="Hello, world!",
        post_type="text",
    )
    test_session.add(post)
    await test_session.flush()

    result = await test_session.get(SocialPost, post.id)
    assert result is not None
    assert result.content == "Hello, world!"
    assert result.moderation_status == "pending"
    assert result.media_urls is None


@pytest.mark.asyncio
async def test_social_post_soft_delete(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(
        author_id=user_id,
        content="Will be deleted",
    )
    test_session.add(post)
    await test_session.flush()

    assert post.is_deleted is False
    post.soft_delete()
    await test_session.flush()

    assert post.is_deleted is True
    assert post.deleted_at is not None


@pytest.mark.asyncio
async def test_social_post_with_media(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(
        author_id=user_id,
        content="Check this out",
        media_urls=["https://example.com/img.png"],
        post_type="image",
    )
    test_session.add(post)
    await test_session.flush()

    result = await test_session.get(SocialPost, post.id)
    assert result.post_type == "image"


# ═══════════════════════════════════════════════════════════════════
# PostComment tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_post_comment(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(author_id=user_id, content="A post")
    test_session.add(post)
    await test_session.flush()

    comment = PostComment(
        post_id=post.id,
        author_id=user_id,
        content="Nice post!",
    )
    test_session.add(comment)
    await test_session.flush()

    result = await test_session.get(PostComment, comment.id)
    assert result is not None
    assert result.content == "Nice post!"
    assert result.moderation_status == "pending"


@pytest.mark.asyncio
async def test_post_comment_soft_delete(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(author_id=user_id, content="A post")
    test_session.add(post)
    await test_session.flush()

    comment = PostComment(post_id=post.id, author_id=user_id, content="Delete me")
    test_session.add(comment)
    await test_session.flush()

    assert comment.is_deleted is False
    comment.soft_delete()
    await test_session.flush()
    assert comment.is_deleted is True


# ═══════════════════════════════════════════════════════════════════
# PostLike tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_post_like(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(author_id=user_id, content="Likeable")
    test_session.add(post)
    await test_session.flush()

    like = PostLike(post_id=post.id, user_id=user_id)
    test_session.add(like)
    await test_session.flush()

    result = await test_session.get(PostLike, like.id)
    assert result is not None


@pytest.mark.asyncio
async def test_post_like_unique_constraint(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(author_id=user_id, content="Like once")
    test_session.add(post)
    await test_session.flush()

    like1 = PostLike(post_id=post.id, user_id=user_id)
    test_session.add(like1)
    await test_session.flush()

    like2 = PostLike(post_id=post.id, user_id=user_id)
    test_session.add(like2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


# ═══════════════════════════════════════════════════════════════════
# Hashtag + PostHashtag tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_hashtag(test_session):
    tag = Hashtag(name="fun")
    test_session.add(tag)
    await test_session.flush()

    result = await test_session.get(Hashtag, tag.id)
    assert result.name == "fun"
    assert result.post_count == 0


@pytest.mark.asyncio
async def test_hashtag_unique_name(test_session):
    t1 = Hashtag(name="unique_tag")
    test_session.add(t1)
    await test_session.flush()

    t2 = Hashtag(name="unique_tag")
    test_session.add(t2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_post_hashtag_association(test_session):
    user_id = await _make_user(test_session)
    post = SocialPost(author_id=user_id, content="Tagged #fun")
    tag = Hashtag(name="fun2")
    test_session.add_all([post, tag])
    await test_session.flush()

    ph = PostHashtag(post_id=post.id, hashtag_id=tag.id)
    test_session.add(ph)
    await test_session.flush()

    result = await test_session.get(PostHashtag, ph.id)
    assert result is not None


# ═══════════════════════════════════════════════════════════════════
# Follow tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_follow(test_session):
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    follow = Follow(follower_id=user1, following_id=user2)
    test_session.add(follow)
    await test_session.flush()

    result = await test_session.get(Follow, follow.id)
    assert result is not None
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_follow_unique_constraint(test_session):
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    f1 = Follow(follower_id=user1, following_id=user2)
    test_session.add(f1)
    await test_session.flush()

    f2 = Follow(follower_id=user1, following_id=user2)
    test_session.add(f2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_follow_reverse_allowed(test_session):
    """A can follow B and B can follow A — they are distinct."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    f1 = Follow(follower_id=user1, following_id=user2, status="accepted")
    f2 = Follow(follower_id=user2, following_id=user1, status="accepted")
    test_session.add_all([f1, f2])
    await test_session.flush()

    assert f1.id != f2.id


# ═══════════════════════════════════════════════════════════════════
# Contact tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_contact(test_session):
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    contact = Contact(requester_id=user1, target_id=user2)
    test_session.add(contact)
    await test_session.flush()

    result = await test_session.get(Contact, contact.id)
    assert result.status == "pending"
    assert result.parent_approval_status == "not_required"


@pytest.mark.asyncio
async def test_contact_unique_constraint(test_session):
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    c1 = Contact(requester_id=user1, target_id=user2)
    test_session.add(c1)
    await test_session.flush()

    c2 = Contact(requester_id=user1, target_id=user2)
    test_session.add(c2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_contact_approval(test_session):
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    parent = await _make_user(test_session)

    contact = Contact(
        requester_id=user1,
        target_id=user2,
        parent_approval_status="pending",
    )
    test_session.add(contact)
    await test_session.flush()

    approval = ContactApproval(
        contact_id=contact.id,
        parent_user_id=parent,
        decision="approved",
        decided_at=datetime.now(timezone.utc),
    )
    test_session.add(approval)
    await test_session.flush()

    result = await test_session.get(ContactApproval, approval.id)
    assert result.decision == "approved"
    assert result.decided_at is not None


# ═══════════════════════════════════════════════════════════════════
# Moderation tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_moderation_queue_item(test_session):
    item = ModerationQueue(
        content_type="post",
        content_id=uuid.uuid4(),
        pipeline="pre_publish",
        age_tier="10-12",
    )
    test_session.add(item)
    await test_session.flush()

    result = await test_session.get(ModerationQueue, item.id)
    assert result.status == "pending"
    assert result.pipeline == "pre_publish"


@pytest.mark.asyncio
async def test_moderation_decision(test_session):
    user_id = await _make_user(test_session)
    item = ModerationQueue(
        content_type="comment",
        content_id=uuid.uuid4(),
        pipeline="post_publish",
    )
    test_session.add(item)
    await test_session.flush()

    decision = ModerationDecision(
        queue_id=item.id,
        moderator_id=user_id,
        action="approve",
        reason="Content is safe",
    )
    test_session.add(decision)
    await test_session.flush()

    result = await test_session.get(ModerationDecision, decision.id)
    assert result.action == "approve"


@pytest.mark.asyncio
async def test_moderation_decision_auto(test_session):
    """Automated decisions have no moderator_id."""
    item = ModerationQueue(
        content_type="media",
        content_id=uuid.uuid4(),
        pipeline="pre_publish",
    )
    test_session.add(item)
    await test_session.flush()

    decision = ModerationDecision(
        queue_id=item.id,
        moderator_id=None,
        action="reject",
        reason="Automated: CSAM detected",
    )
    test_session.add(decision)
    await test_session.flush()

    result = await test_session.get(ModerationDecision, decision.id)
    assert result.moderator_id is None


@pytest.mark.asyncio
async def test_content_report(test_session):
    user_id = await _make_user(test_session)
    report = ContentReport(
        reporter_id=user_id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="Inappropriate content",
    )
    test_session.add(report)
    await test_session.flush()

    result = await test_session.get(ContentReport, report.id)
    assert result.status == "pending"
    assert result.reason == "Inappropriate content"


@pytest.mark.asyncio
async def test_media_asset(test_session):
    user_id = await _make_user(test_session)
    asset = MediaAsset(
        cloudflare_r2_key="uploads/abc123.jpg",
        media_type="image",
        owner_id=user_id,
        content_length=1024,
    )
    test_session.add(asset)
    await test_session.flush()

    result = await test_session.get(MediaAsset, asset.id)
    assert result.moderation_status == "pending"
    assert result.content_length == 1024


# ═══════════════════════════════════════════════════════════════════
# Governance tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_governance_policy(test_session):
    group, owner_id = await _make_user_and_group(test_session)
    policy = GovernancePolicy(
        school_id=group.id,
        state_code="OH",
        policy_type="ai_usage",
        content={"rules": ["No ChatGPT during tests"]},
    )
    test_session.add(policy)
    await test_session.flush()

    result = await test_session.get(GovernancePolicy, policy.id)
    assert result.status == "draft"
    assert result.version == 1
    assert result.state_code == "OH"


@pytest.mark.asyncio
async def test_governance_audit(test_session):
    group, owner_id = await _make_user_and_group(test_session)
    policy = GovernancePolicy(
        school_id=group.id,
        state_code="CA",
        policy_type="governance",
        content={"v1": True},
    )
    test_session.add(policy)
    await test_session.flush()

    audit = GovernanceAudit(
        policy_id=policy.id,
        action="created",
        actor_id=owner_id,
        diff={"added": {"v1": True}},
    )
    test_session.add(audit)
    await test_session.flush()

    result = await test_session.get(GovernanceAudit, audit.id)
    assert result.action == "created"


# ═══════════════════════════════════════════════════════════════════
# Messaging tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_conversation(test_session):
    user_id = await _make_user(test_session)
    conv = Conversation(type="direct", created_by=user_id)
    test_session.add(conv)
    await test_session.flush()

    result = await test_session.get(Conversation, conv.id)
    assert result.type == "direct"
    assert result.title is None


@pytest.mark.asyncio
async def test_conversation_member(test_session):
    user_id = await _make_user(test_session)
    conv = Conversation(type="group", created_by=user_id, title="Study group")
    test_session.add(conv)
    await test_session.flush()

    member = ConversationMember(
        conversation_id=conv.id,
        user_id=user_id,
        role="admin",
    )
    test_session.add(member)
    await test_session.flush()

    result = await test_session.get(ConversationMember, member.id)
    assert result.role == "admin"
    assert result.last_read_at is None


@pytest.mark.asyncio
async def test_create_message(test_session):
    user_id = await _make_user(test_session)
    conv = Conversation(type="direct", created_by=user_id)
    test_session.add(conv)
    await test_session.flush()

    msg = Message(
        conversation_id=conv.id,
        sender_id=user_id,
        content="Hello!",
    )
    test_session.add(msg)
    await test_session.flush()

    result = await test_session.get(Message, msg.id)
    assert result.content == "Hello!"
    assert result.message_type == "text"
    assert result.moderation_status == "pending"


@pytest.mark.asyncio
async def test_message_media(test_session):
    user_id = await _make_user(test_session)
    conv = Conversation(type="direct", created_by=user_id)
    test_session.add(conv)
    await test_session.flush()

    msg = Message(
        conversation_id=conv.id,
        sender_id=user_id,
        content="Photo",
        message_type="image",
    )
    test_session.add(msg)
    await test_session.flush()

    media = MessageMedia(
        message_id=msg.id,
        cloudflare_id="cf_img_abc123",
        media_type="image",
    )
    test_session.add(media)
    await test_session.flush()

    result = await test_session.get(MessageMedia, media.id)
    assert result.cloudflare_id == "cf_img_abc123"
    assert result.moderation_status == "pending"


# ═══════════════════════════════════════════════════════════════════
# FK relationship tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_post_comment_fk_to_post(test_session):
    """Comment must reference a valid post."""
    user_id = await _make_user(test_session)
    comment = PostComment(
        post_id=uuid.uuid4(),  # non-existent post
        author_id=user_id,
        content="Orphan comment",
    )
    test_session.add(comment)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_post_like_fk_to_post(test_session):
    """Like must reference a valid post."""
    user_id = await _make_user(test_session)
    like = PostLike(
        post_id=uuid.uuid4(),  # non-existent post
        user_id=user_id,
    )
    test_session.add(like)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_follow_fk_to_user(test_session):
    """Follow must reference valid users."""
    user_id = await _make_user(test_session)
    follow = Follow(
        follower_id=user_id,
        following_id=uuid.uuid4(),  # non-existent
    )
    test_session.add(follow)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_contact_approval_fk_to_contact(test_session):
    """ContactApproval must reference a valid contact."""
    user_id = await _make_user(test_session)
    approval = ContactApproval(
        contact_id=uuid.uuid4(),  # non-existent
        parent_user_id=user_id,
        decision="approved",
    )
    test_session.add(approval)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_message_fk_to_conversation(test_session):
    """Message must reference a valid conversation."""
    user_id = await _make_user(test_session)
    msg = Message(
        conversation_id=uuid.uuid4(),  # non-existent
        sender_id=user_id,
        content="Orphan message",
    )
    test_session.add(msg)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


# ═══════════════════════════════════════════════════════════════════
# Migration verification tests
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_profiles_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM profiles"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_social_posts_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM social_posts"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_post_comments_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM post_comments"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_post_likes_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM post_likes"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_hashtags_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM hashtags"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_follows_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM follows"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_contacts_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM contacts"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_moderation_queue_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM moderation_queue"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_governance_policies_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM governance_policies"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_conversations_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM conversations"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_messages_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM messages"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_media_assets_table_exists(test_session):
    result = await test_session.execute(text("SELECT count(*) FROM media_assets"))
    assert result.scalar() == 0
