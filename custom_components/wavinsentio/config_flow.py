import logging

from typing import Any, Dict, Optional

from homeassistant import config_entries, core
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import voluptuous as vol
from wavinsentio.wavinsentio import WavinSentio

from .const import DOMAIN, CONF_LOCATION_ID

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
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
            return await self.async_step_location()

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_location(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to choose the location"""
        errors: Dict[str, str] = {}
        api = await self.hass.async_add_executor_job(
            WavinSentio, self.data[CONF_USERNAME], self.data[CONF_PASSWORD]
        )

        locations = await self.hass.async_add_executor_job(api.get_locations)

        all_locations = {l["ulc"]: l["name"] for l in locations}

        if user_input is not None:
            self.data[CONF_LOCATION_ID] = user_input[CONF_LOCATION_ID]
            return self.async_create_entry(title="Wavin Sentio", data=self.data)

        LOCATION_SCHEMA = vol.Schema(
            {vol.Optional(CONF_LOCATION_ID): vol.In(all_locations)}
        )

        return self.async_show_form(
            step_id="location", data_schema=LOCATION_SCHEMA, errors=errors
        )