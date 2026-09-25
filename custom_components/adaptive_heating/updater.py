"""Manual GitHub release checks and user-initiated installation. No polling."""

import asyncio
import json
from pathlib import Path
from zipfile import BadZipFile

from aiohttp import ClientError
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, REPOSITORY, VERSION
from .release import MAX_ARCHIVE_BYTES, install_files, release_info, validate_archive, version_tuple


class ReleaseManager:
    def __init__(self, hass):
        self.hass = hass
        self.info = None
        self.controllers = set()
        self.restart_pending = False
        self.in_progress = False
        self.backup_path = None
        self.last_error = None
        self.lock = asyncio.Lock()

    def notify(self):
        for controller in self.controllers:
            controller.async_update_listeners()

    async def fetch(self, url, limit):
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(45):
            async with session.get(url, headers={"Accept": "application/vnd.github+json" if "api.github.com" in url else "application/octet-stream"}) as response:
                if response.status != 200:
                    raise ValueError(f"GitHub returned HTTP {response.status}")
                data = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    data.extend(chunk)
                    if len(data) > limit:
                        raise ValueError("Download exceeds expected size")
                return bytes(data)

    async def async_check(self):
        async with self.lock:
            try:
                data = await self.fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/latest", 512000)
                self.info = release_info(json.loads(data))
                self.last_error = None
            except (ClientError, TimeoutError, ValueError, TypeError, KeyError, AttributeError) as err:
                self.last_error = str(err)
                raise HomeAssistantError(f"Could not check releases: {err}") from err
            finally:
                self.notify()

    async def async_install(self):
        if self.info is None:
            await self.async_check()
        async with self.lock:
            if self.restart_pending:
                raise HomeAssistantError("An update is already installed; restart when ready")
            info = dict(self.info)
            if version_tuple(info["version"]) <= version_tuple(VERSION):
                raise HomeAssistantError("No newer stable release is selected")
            self.in_progress = True
            self.last_error = None
            self.notify()
            try:
                # Download and validate before changing any installed file.
                blob = await self.fetch(info["url"], MAX_ARCHIVE_BYTES)
                checksum = (await self.fetch(info["checksum_url"], 1024)).decode("ascii")
                files = await self.hass.async_add_executor_job(validate_archive, blob, checksum, info["version"], HA_VERSION)
                # Wait for any in-flight controller command to finish, then pause
                # each controller before replacing code. No automatic HA restart.
                for controller in list(self.controllers):
                    await controller.async_ac_mode("observe")
                    if controller.ac.session or controller.ac.recovery_pending:
                        raise HomeAssistantError("Wait for AC restoration before installing an update")
                    await controller.async_disinfection_mode("observe")
                    if controller.disinfection.blocks_heating:
                        raise HomeAssistantError("Wait for tank target restoration before installing an update")
                    await controller.async_mode("observe")
                self.backup_path = await self.hass.async_add_executor_job(
                    install_files, files, Path(__file__).resolve().parent,
                    Path(self.hass.config.path(".adaptive_heating_backups")))
                self.restart_pending = True
            except (HomeAssistantError, ClientError, TimeoutError, ValueError, OSError, UnicodeError, SyntaxError, BadZipFile, AttributeError, TypeError) as err:
                self.last_error = str(err)
                raise HomeAssistantError(f"Update was not installed: {err}") from err
            finally:
                self.in_progress = False
                self.notify()
