"""Authentication & authorization module."""

# Public interface for cross-module access
from .middleware import get_current_user
from .models import OAuthConnection, Session, User
from .service import decode_token
