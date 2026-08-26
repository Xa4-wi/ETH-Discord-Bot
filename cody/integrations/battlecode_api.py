"""Compatibility import for Cody's single Main Backend integration client.

New code should import from :mod:`cody.integrations.backend`. Cody must not add
feature-specific raw HTTP clients or communicate with match infrastructure.
"""

from cody.integrations.backend import BackendAction, MainBackendClient


__all__ = ("BackendAction", "MainBackendClient")
