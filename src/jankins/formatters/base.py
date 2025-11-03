"""Base formatter types and utilities."""

from enum import Enum
from typing import Any, Dict, List


class OutputFormat(str, Enum):
    """Output format options for tool responses."""

    SUMMARY = "summary"  # Minimal, token-efficient summary
    FULL = "full"        # Complete data with all fields
    DIFF = "diff"        # Differences only (for comparisons)
    IDS = "ids"          # IDs and URLs only
    TABLE = "table"      # Compact table format


def compact_dict(data: Dict[str, Any], include_keys: List[str]) -> Dict[str, Any]:
    """Extract only specified keys from dict."""
    return {k: data.get(k) for k in include_keys if k in data}


def format_duration(milliseconds: int) -> str:
    """Format duration in human-readable form."""
    if milliseconds < 1000:
        return f"{milliseconds}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.1f}s"
    elif milliseconds < 3600000:
        minutes = milliseconds // 60000
        seconds = (milliseconds % 60000) // 1000
        return f"{minutes}m {seconds}s"
    else:
        hours = milliseconds // 3600000
        minutes = (milliseconds % 3600000) // 60000
        return f"{hours}h {minutes}m"


def format_timestamp(timestamp_ms: int) -> str:
    """Format Unix timestamp in milliseconds to ISO string."""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
