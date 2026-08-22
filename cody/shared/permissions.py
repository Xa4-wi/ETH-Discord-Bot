"""Reusable application-command permission checks."""

from discord import app_commands


def administrator_only():
    return app_commands.checks.has_permissions(administrator=True)
