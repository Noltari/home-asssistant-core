"""Support for OpenWrt ubus devices."""
from typing import Dict

from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import HomeAssistantType

from .const import DEFAULT_DEVICE_NAME, DOMAIN
from .router import OpenWrtRouter


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up device tracker for OpenWrt ubus component."""
    router = hass.data[DOMAIN][entry.unique_id]
    tracked = set()

    @callback
    def update_router():
        """Update the values of the router."""
        add_entities(router, async_add_entities, tracked)

    router.listeners.append(
        async_dispatcher_connect(hass, router.signal_device_new, update_router)
    )

    update_router()


@callback
def add_entities(router, async_add_entities, tracked):
    """Add new tracker entities from the router."""
    new_tracked = []

    for mac in router.devices.keys():
        if mac in tracked:
            continue

        new_tracked.append(OpenWrtDevice(router, mac))
        tracked.add(mac)

    if new_tracked:
        async_add_entities(new_tracked, True)


class OpenWrtDevice(ScannerEntity):
    """Representation of a OpenWrt ubus device."""

    def __init__(self, router: OpenWrtRouter, mac) -> None:
        """Initialize a OpenWrt ubus device."""
        self._router = router
        self._name = DEFAULT_DEVICE_NAME
        self._mac = mac
        self._active = False

    @callback
    def async_update_state(self) -> None:
        """Update the OpenWrt ubus device."""
        self._active = self._router.devices[self._mac]["authorized"]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._mac

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self._active

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SOURCE_TYPE_ROUTER

    @property
    def device_info(self) -> Dict[str, any]:
        """Return the device information."""
        return {
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "OpenWrt Tracked device",
        }

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @callback
    def async_on_demand_update(self):
        """Update state."""
        self.async_update_state()
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Register state update callback."""
        self.async_update_state()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._router.signal_device_update,
                self.async_on_demand_update,
            )
        )
