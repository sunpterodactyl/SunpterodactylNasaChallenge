"""Vercel entrypoint. The real app lives in backend.api.index."""

from backend.api.index import app

__all__ = ['app']
