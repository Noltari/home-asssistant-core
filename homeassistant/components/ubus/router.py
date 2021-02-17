"""Represent the OpenWrt router and its devices and sensors."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from openwrt.ubus import Ubus

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)


class OpenWrtRouter:
    """Representation of an OpenWrt router."""

    def __init__(self, hass: HomeAssistantType, entry: ConfigEntry) -> None:
        """Initialize an OpenWrt router."""
        self.hass = hass
        self.entry = entry
        self.url = entry.data[CONF_URL]
        self.ubus = Ubus(self.url, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

        self.dist = None
        self.name = None
        self.sw_version = None

        self.devices: Dict[str, Any] = {}

        self.hostapd = None
        self.unsub_dispatcher = None

    async def setup(self) -> None:
        """Set up an OpenWrt router."""
        session = await self.ubus.connect()
        if not session:
            return ConfigEntryNotReady

        # Hostapd
        self.hostapd = self.ubus.get_hostapd()

        # System
        board = await self.ubus.system.board()
        release = board["release"]

        self.dist = board["distribution"]
        self.name = board["model"]
        self.sw_version = f"{release['version']}-{release['revision']}"

        # Devices & sensors
        await self.update_all()
        self.unsub_dispatcher = async_track_time_interval(
            self.hass, self.update_all, SCAN_INTERVAL
        )

    async def update_all(self, now: Optional[datetime] = None) -> None:
        """Update all OpenWrt ubus platforms."""
        await self.update_devices()

    async def update_devices(self) -> None:
        """Update OpenWrt ubus devices."""
        new_device = False

        for hostapd in self.hostapd:
            res = self.ubus.get_hostapd_clients(hostapd)
            if res:
                clients = res["clients"]
                for key in clients.keys():
                    if self.devices.get(key) is None:
                        new_device = True

                    self.devices[key] = clients[key]

        async_dispatcher_send(self.hass, self.signal_device_update)

        if new_device:
            async_dispatcher_send(self.hass, self.signal_device_new)

    async def reboot(self) -> None:
        """Reboot the OpenWrt router."""
        await self.ubus.system_reboot()

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.url)},
            "name": self.name,
            "manufacturer": self.dist,
            "sw_version": self.sw_version,
        }

    @property
    def signal_device_new(self) -> str:
        """Event specific per OpenWrt ubus entry to signal new device."""
        return f"{DOMAIN}-{self.url}-device-new"

    @property
    def signal_device_update(self) -> str:
        """Event specific per OpenWrt ubus entry to signal updates in devices."""
        return f"{DOMAIN}-{self.url}-device-update"
