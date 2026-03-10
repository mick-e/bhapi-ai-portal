"""Auto-provisioning of group members on SSO login."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import MAX_FAMILY_MEMBERS, MAX_GROUP_MEMBERS
from src.groups.models import Group, GroupMember
from src.integrations.sso_models import SSOConfig

logger = structlog.get_logger()


async def auto_provision_member(
    db: AsyncSession,
    group_id: UUID,
    sso_user_info: dict,
) -> GroupMember | None:
    """Auto-create a group member on SSO login when SSOConfig exists for the group.

    Checks for an existing member by external_id (via user lookup) before creating.
    Respects family member cap of 5 (MAX_FAMILY_MEMBERS).
    Returns the existing member if already provisioned, or the newly created member.
    Returns None if no SSO config, provisioning disabled, or cap reached.

    Expected sso_user_info keys:
        - email: str (required)
        - display_name: str (optional, falls back to email local part)
        - external_id: str (provider-specific user identifier)
    """
    email = sso_user_info.get("email")
    display_name = sso_user_info.get("display_name", "")
    external_id = sso_user_info.get("external_id", "")

    if not email:
        logger.warning("sso_provision_no_email", group_id=str(group_id))
        return None

    # Load SSO config for the group
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.group_id == group_id)
    )
    sso_config = result.scalar_one_or_none()
    if not sso_config:
        logger.warning("sso_provision_config_not_found", group_id=str(group_id))
        return None

    if not sso_config.auto_provision_members:
        logger.debug(
            "sso_provision_disabled",
            group_id=str(group_id),
            config_id=str(sso_config.id),
        )
        return None

    # Load group to determine type and cap
    group_result = await db.execute(
        select(Group).where(Group.id == group_id)
    )
    group = group_result.scalar_one_or_none()
    if not group:
        logger.warning("sso_provision_group_not_found", group_id=str(group_id))
        return None

    # Check if member with this email already exists via User lookup
    from src.auth.models import User

    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()

    if user:
        existing_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user.id,
            )
        )
        existing_member = existing_result.scalar_one_or_none()
        if existing_member:
            logger.debug(
                "sso_provision_member_exists",
                email=email,
                group_id=str(group_id),
                member_id=str(existing_member.id),
            )
            return existing_member

    # Check member cap — family cap is 5, school/club have MAX_GROUP_MEMBERS
    cap = MAX_FAMILY_MEMBERS if group.type == "family" else MAX_GROUP_MEMBERS
    count_result = await db.execute(
        select(func.count(GroupMember.id)).where(
            GroupMember.group_id == group_id
        )
    )
    count = count_result.scalar() or 0
    if count >= cap:
        logger.warning(
            "sso_provision_cap_reached",
            group_id=str(group_id),
            group_type=group.type,
            cap=cap,
            current=count,
        )
        return None

    # Create the member
    member = GroupMember(
        id=uuid4(),
        group_id=group_id,
        user_id=user.id if user else None,
        role="member",
        display_name=display_name or email.split("@")[0],
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    logger.info(
        "sso_member_provisioned",
        member_id=str(member.id),
        group_id=str(group_id),
        email=email,
        external_id=external_id,
    )
    return member
