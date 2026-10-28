"""Auto Custom Icons: pick a folder, drop SVGs in, use them as prefix:name. No reloads."""
from __future__ import annotations

import logging
import os
from functools import partial

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_FOLDER,
    CONF_PREFIX,
    DOMAIN,
    LOADER_URL,
    SCAN_INTERVAL,
    SIGNAL_CHANGED,
    VERSION,
)
from .icons import list_icons, read_icon, scan

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class FolderWatcher:
    """Polls a folder every few seconds and pings the frontend when it changes."""

    def __init__(self, hass: HomeAssistant, prefix: str, root: str) -> None:
        self.hass = hass
        self.prefix = prefix
        self.root = root
        self._snapshot: dict | None = None
        self._unsub = None
        self._busy = False

    async def async_start(self) -> None:
        self._snapshot = await self.hass.async_add_executor_job(scan, self.root)
        self._unsub = async_track_time_interval(self.hass, self._tick, SCAN_INTERVAL)

    async def _tick(self, _now) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            snap = await self.hass.async_add_executor_job(scan, self.root)
        finally:
            self._busy = False
        if snap != self._snapshot:
            self._snapshot = snap
            async_dispatcher_send(
                self.hass, SIGNAL_CHANGED, {"prefix": self.prefix, "kind": "icons"}
            )

    @callback
    def stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


# ---------------------------------------------------------------- websocket API


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/prefixes"})
@callback
def ws_prefixes(hass: HomeAssistant, connection, msg: dict) -> None:
    connection.send_result(msg["id"], sorted(hass.data[DOMAIN]["roots"]))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/list", vol.Required("prefix"): str}
)
@websocket_api.async_response
async def ws_list(hass: HomeAssistant, connection, msg: dict) -> None:
    root = hass.data[DOMAIN]["roots"].get(msg["prefix"])
    if root is None:
        connection.send_result(msg["id"], [])
        return
    names = await hass.async_add_executor_job(list_icons, root)
    connection.send_result(msg["id"], [{"name": n} for n in names])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/icon",
        vol.Required("prefix"): str,
        vol.Required("icon"): str,
    }
)
@websocket_api.async_response
async def ws_icon(hass: HomeAssistant, connection, msg: dict) -> None:
    root = hass.data[DOMAIN]["roots"].get(msg["prefix"])
    if root is None:
        connection.send_result(msg["id"], None)
        return
    data = await hass.async_add_executor_job(read_icon, root, msg["icon"])
    connection.send_result(msg["id"], data)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection, msg: dict) -> None:
    """Push 'something changed' to the browser so it never needs a manual reload."""

    @callback
    def forward(payload: dict) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], payload))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_CHANGED, forward
    )
    connection.send_result(msg["id"])


# ---------------------------------------------------------------------- setup


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {"roots": {}, "watchers": {}})

    for cmd in (ws_prefixes, ws_list, ws_icon, ws_subscribe):
        websocket_api.async_register_command(hass, cmd)

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                LOADER_URL,
                os.path.join(os.path.dirname(__file__), "loader.js"),
                False,
            )
        ]
    )
    add_extra_js_url(hass, f"{LOADER_URL}?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    folder = entry.data[CONF_FOLDER]
    prefix = entry.data[CONF_PREFIX]
    root = hass.config.path(folder)

    await hass.async_add_executor_job(partial(os.makedirs, root, exist_ok=True))

    watcher = FolderWatcher(hass, prefix, root)
    await watcher.async_start()

    data = hass.data[DOMAIN]
    data["roots"][prefix] = root
    data["watchers"][entry.entry_id] = watcher

    async_dispatcher_send(hass, SIGNAL_CHANGED, {"prefix": prefix, "kind": "entries"})
    _LOGGER.info("Auto Custom Icons watching %s as '%s:'", root, prefix)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN]
    watcher = data["watchers"].pop(entry.entry_id, None)
    if watcher:
        watcher.stop()
    data["roots"].pop(entry.data[CONF_PREFIX], None)
    async_dispatcher_send(
        hass, SIGNAL_CHANGED, {"prefix": entry.data[CONF_PREFIX], "kind": "entries"}
    )
    return True
