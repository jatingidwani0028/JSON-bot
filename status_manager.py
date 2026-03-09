"""
Status manager — helpers for status validation and display.
"""

VALID_STATUSES = {"USED", "UNUSED"}

STATUS_EMOJI = {
    "USED": "✅",
    "UNUSED": "🔄",
}


def is_valid_status(status: str) -> bool:
    return status.upper() in VALID_STATUSES


def format_status(status: str) -> str:
    emoji = STATUS_EMOJI.get(status.upper(), "❓")
    return f"{emoji} {status.upper()}"
