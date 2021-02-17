"""Config flow to configure the OpenWrt ubus integration."""
import logging

from openwrt.ubus import Ubus
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_URL, CONF_USERNAME

# pylint:disable=unused-import
from .const import DEFAULT_NAME, DOMAIN, RESULT_UNKNOWN

_LOGGER = logging.getLogger(__name__)


class UbusFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(f"{url}")
            self._abort_if_unique_id_configured()

            ubus_online = await _is_ubus_rpc_online(self.hass, url, username, password)
            if not ubus_online:
                errors["base"] = RESULT_UNKNOWN

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_USERNAME): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


async def _is_ubus_rpc_online(hass, url, username, password):
    ubus = Ubus(url, username, password)
    return await hass.async_add_executor_job(ubus.connect, False)
