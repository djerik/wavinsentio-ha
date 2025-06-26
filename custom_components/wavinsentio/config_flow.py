import logging

from typing import Any, Dict, Optional

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
import voluptuous as vol
from .wavinsentio import Device, WavinSentio, UnauthorizedException

from .const import CONF_DEVICE_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)


class WavinSentioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Wavin Sentio config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input

            # Return the form of the next step.
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_device(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to choose the device."""
        if user_input is not None:
            self.data[CONF_DEVICE_NAME] = user_input[CONF_DEVICE_NAME]
            return await self.async_create_entry(title="Wavin Sentio", data=self.data)

        errors = {}
        try:
            api = await self.hass.async_add_executor_job(
                WavinSentio, self.data[CONF_EMAIL], self.data[CONF_PASSWORD]
            )
        except UnauthorizedException as err:
            errors["base"] = "auth_error"
            return self.async_show_form(
                step_id="user", data_schema=AUTH_SCHEMA, errors=errors
            )

        devices = await self.hass.async_add_executor_job(api.get_devices)

        all_devices = {d.name:d.lastConfig.sentio.titlePersonalized for d in devices}

        DEVICE_SCHEMA = vol.Schema(
            {vol.Optional(CONF_DEVICE_NAME): vol.In(all_devices)}
        )

        return self.async_show_form(
            step_id="device", data_schema=DEVICE_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        return await self.async_step_user()

    async def async_create_entry(self, title: str, data: dict) -> dict:
        """Create an oauth config entry or update existing entry for reauth."""
        # TODO: This example supports only a single config entry. Consider
        # any special handling needed for multiple config entries.
        existing_entry = await self.async_set_unique_id(data[CONF_DEVICE_NAME])
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return super().async_create_entry(title=title, data=data)
