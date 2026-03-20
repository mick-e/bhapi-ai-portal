"""Contacts — contact requests, parent approval, blocking.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.contacts.service import (
    approve_as_parent,
    block_contact,
    get_pending_approvals,
    list_contacts,
    respond_to_request,
    send_request,
)

__all__ = [
    "approve_as_parent",
    "block_contact",
    "get_pending_approvals",
    "list_contacts",
    "respond_to_request",
    "send_request",
]
