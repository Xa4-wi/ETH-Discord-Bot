"""No canonical database adapter is permitted inside Cody.

Competition data and future durable ticket state belong to the Main Backend.
This module intentionally exposes no connection, query, or migration API; it is
retained only to make the boundary explicit while older planning references are
removed.
"""
