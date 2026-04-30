"""Grant a test subscription to a user without going through Stripe.

Used for internal test accounts that need paid-tier features unlocked
(API keys, OAuth clients, webhooks, intelligence dashboards) without
running a real Stripe checkout. Idempotent — safe to re-run.

Usage (from a Render Shell on the bhapi-core-api service):

    python scripts/grant_test_subscription.py mpesber@gmail.com
    python scripts/grant_test_subscription.py mpesber@gmail.com --plan family --days 90
    python scripts/grant_test_subscription.py mpesber@gmail.com --revoke

Behaviour:
  * Looks up the user by exact email match.
  * Resolves their group_id (User.group_id, NOT NULL on registration).
  * If the group already has a Subscription row, the existing row is updated.
    Otherwise a new row is inserted. Either way, exactly one active row
    per group remains after the run.
  * stripe_customer_id and stripe_subscription_id stay NULL — there is no
    Stripe-side state. Cancelling the test entitlement is a single DB
    update via ``--revoke`` (sets status='cancelled' and clears period_end).
  * All work happens inside a single transaction. Aborts and rolls back
    on any exception, leaving the row untouched.

Exit codes:
    0  success
    1  user not found
    2  invalid plan_type or other usage error
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select

from src.auth.models import User
from src.billing.models import Subscription
from src.billing.plans import PLAN_TIERS
from src.database import async_session_maker, engine

logger = structlog.get_logger("grant_test_subscription")


VALID_PLANS: set[str] = set(PLAN_TIERS.keys())


async def _grant(email: str, plan: str, days: int, revoke: bool) -> int:
    async with async_session_maker() as session:
        async with session.begin():
            user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                logger.error("user_not_found", email=email)
                return 1

            existing = (
                await session.execute(
                    select(Subscription).where(Subscription.group_id == user.group_id)
                )
            ).scalar_one_or_none()

            if revoke:
                if existing is None:
                    logger.warning("no_subscription_to_revoke", email=email, user_id=str(user.id))
                    return 0
                existing.status = "cancelled"
                existing.current_period_end = datetime.now(timezone.utc)
                logger.info(
                    "subscription_revoked",
                    email=email,
                    user_id=str(user.id),
                    group_id=str(user.group_id),
                    subscription_id=str(existing.id),
                )
                return 0

            new_period_end = datetime.now(timezone.utc) + timedelta(days=days)

            if existing is None:
                sub = Subscription(
                    group_id=user.group_id,
                    plan_type=plan,
                    billing_cycle="monthly",
                    status="active",
                    current_period_end=new_period_end,
                    stripe_customer_id=None,
                    stripe_subscription_id=None,
                )
                session.add(sub)
                await session.flush()
                logger.info(
                    "subscription_created",
                    email=email,
                    user_id=str(user.id),
                    group_id=str(user.group_id),
                    subscription_id=str(sub.id),
                    plan=plan,
                    current_period_end=new_period_end.isoformat(),
                )
            else:
                logger.info(
                    "subscription_updated",
                    email=email,
                    user_id=str(user.id),
                    group_id=str(user.group_id),
                    subscription_id=str(existing.id),
                    old_plan=existing.plan_type,
                    new_plan=plan,
                    old_status=existing.status,
                    new_status="active",
                    old_period_end=(
                        existing.current_period_end.isoformat()
                        if existing.current_period_end
                        else None
                    ),
                    new_period_end=new_period_end.isoformat(),
                )
                existing.plan_type = plan
                existing.status = "active"
                existing.current_period_end = new_period_end
                existing.stripe_customer_id = None
                existing.stripe_subscription_id = None

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("email", help="User email (exact match) to grant subscription to")
    parser.add_argument(
        "--plan",
        default="family_plus",
        help=f"Plan tier (default: family_plus). One of: {sorted(VALID_PLANS)}",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Days until current_period_end (default: 365)",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Cancel the existing subscription instead of granting one",
    )
    args = parser.parse_args()

    if args.plan not in VALID_PLANS:
        logger.error("invalid_plan", plan=args.plan, valid=sorted(VALID_PLANS))
        return 2

    if args.days < 1 or args.days > 36500:
        logger.error("invalid_days", days=args.days)
        return 2

    try:
        return asyncio.run(_grant(args.email, args.plan, args.days, args.revoke))
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    sys.exit(main())
