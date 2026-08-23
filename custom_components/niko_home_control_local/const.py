"""Constants for the Niko Home Control integration."""

from __future__ import annotations

DOMAIN = "niko_home_control_local"
NAME = "Niko Home Control II"
VERSION = "1.5.0"
DEVELOPER = "Maarten Moortgat"

DEFAULT_PORT = 8884
DEFAULT_USERNAME = "hobby"
DEFAULT_CLIENT_ID_PREFIX = "HomeAssistantNiko"
DEFAULT_CONNECT_TIMEOUT = 15.0
DEFAULT_DEVICE_LIST_TIMEOUT = 15.0

CONF_TOKEN = "token"

PLATFORMS = ["binary_sensor", "cover", "light", "sensor", "switch"]
