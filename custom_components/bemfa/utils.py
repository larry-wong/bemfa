"""Support for bemfa service."""

import logging
from typing import Any

_LOGGING = logging.getLogger(__name__)


def has_key(data: Any, key: str) -> bool:
    """Whether data has specific valid key."""
    return key in data and data[key] is not None
