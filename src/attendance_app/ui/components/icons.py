"""Replaceable shared mapping using only the Phosphor outline family."""
import qtawesome as qta
from attendance_app.ui.styles.theme import PRIMARY, SECONDARY

ICONS = {
    "search": "ph.magnifying-glass",
    "dashboard": "ph.squares-four", "attendance": "ph.camera",
    "people": "ph.users", "history": "ph.clock-counter-clockwise",
    "reports": "ph.chart-bar", "settings": "ph.gear",
}


def icon(name: str, active: bool = False):
    return qta.icon(ICONS[name], color=PRIMARY if active else SECONDARY)
