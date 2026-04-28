"""API module - Routes and schemas."""

from .routes import app, router
from . import schemas

__all__ = ["app", "router", "schemas"]
