"""Contacts — contact requests, parent approval, blocking.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

# Public interface for cross-module access
from .models import Contact

from src.contacts.service import (
    approve_as_parent,
    batch_approve_as_parent,
    block_contact,
    get_pending_approvals,
    get_pending_with_profiles,
    list_contacts,
    respond_to_request,
    send_request,
)

__all__ = [
    "approve_as_parent",
    "batch_approve_as_parent",
    "block_contact",
    "get_pending_approvals",
    "get_pending_with_profiles",
    "list_contacts",
    "respond_to_request",
    "send_request",
    "Contact",
]
