"""Constants for Auto Custom Icons."""
from datetime import timedelta

DOMAIN = "auto_custom_icons"
VERSION = "1.0.0"

CONF_FOLDER = "folder"
CONF_PREFIX = "prefix"

SIGNAL_CHANGED = f"{DOMAIN}_changed"
SCAN_INTERVAL = timedelta(seconds=3)

LOADER_URL = f"/{DOMAIN}/loader.js"
