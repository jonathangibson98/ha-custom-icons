"""Config flow: pick the folder name (and optional prefix) for a set of icons."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_FOLDER, CONF_PREFIX, DOMAIN

FOLDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
PREFIX_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")

# Folders in /config you really don't want to point this at.
RESERVED_FOLDERS = {
    "custom_components", "www", "blueprints", "packages", "themes", "deps",
    "tts", "backups", "media", "esphome", "image", "config",
}
# Prefixes the HA frontend (or other icon packs) already uses.
RESERVED_PREFIXES = {
    "mdi", "hass", "phu", "fapro", "far", "fas", "fab", "fa",
    "simple-icons", "si",
}


class AutoIconsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add one folder of SVG icons."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        user_input = user_input or {}

        if self.source == "user" and user_input:
            folder = user_input[CONF_FOLDER].strip().strip("/")
            prefix = (user_input.get(CONF_PREFIX) or folder).strip().lower()

            if not FOLDER_RE.match(folder):
                errors[CONF_FOLDER] = "invalid_folder"
            elif folder.lower() in RESERVED_FOLDERS:
                errors[CONF_FOLDER] = "reserved_folder"
            elif not PREFIX_RE.match(prefix):
                errors[CONF_PREFIX] = "invalid_prefix"
            elif prefix in RESERVED_PREFIXES:
                errors[CONF_PREFIX] = "reserved_prefix"
            else:
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_FOLDER) == folder:
                        errors[CONF_FOLDER] = "folder_in_use"
                    if entry.data.get(CONF_PREFIX) == prefix:
                        errors[CONF_PREFIX] = "prefix_in_use"

            if not errors:
                await self.async_set_unique_id(prefix)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{prefix}: (/config/{folder})",
                    data={CONF_FOLDER: folder, CONF_PREFIX: prefix},
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_FOLDER, default=user_input.get(CONF_FOLDER, "my_icons")
                ): str,
                vol.Optional(
                    CONF_PREFIX, description={"suggested_value": user_input.get(CONF_PREFIX)}
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
