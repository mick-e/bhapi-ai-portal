"""Unified dashboard API for cross-product consumption."""

import structlog
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def get_unified_dashboard(db: AsyncSession, group_id: UUID) -> dict:
    """Get unified dashboard data aggregating across products."""
    from src.portal.service import get_dashboard
    from src.integrations.cross_product import list_cross_product_alerts

    # Get standard dashboard data
    try:
        dashboard = await get_dashboard(db, group_id)
        dashboard_data = dashboard if isinstance(dashboard, dict) else {}
    except Exception:
        dashboard_data = {}

    # Get cross-product alerts
    try:
        xp_alerts = await list_cross_product_alerts(db, group_id, limit=10)
        xp_alert_data = [
            {
                "id": str(a.id),
                "source_product": a.source_product,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "body": a.body,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in xp_alerts
        ]
    except Exception:
        xp_alert_data = []

    return {
        "dashboard": dashboard_data,
        "cross_product_alerts": xp_alert_data,
        "products": {
            "portal": {"status": "connected", "last_sync": None},
            "app": {"status": "not_connected", "last_sync": None},
            "extension": {"status": "not_connected", "last_sync": None},
        },
    }
