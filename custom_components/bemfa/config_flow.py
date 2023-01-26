"""Config flow for bemfa integration."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_INCLUDE_ENTITIES, CONF_UID, DOMAIN
from .service import BemfaService

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_UID): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for bemfa."""

    VERSION = 1

    # Bemfa service uses uid to auth api calls. One shall provide his uid to config this integration.
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, last_step=True
            )

        # uid should match this regExp
        if not re.match("^[0-9a-f]{32}$", user_input[CONF_UID]):
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "invalid_uid"},
                last_step=True,
            )

        # Multiply integration instances with same uid may case unexpected results.
        # We treat the md5sum of each configured uid as unique.
        uid_md5 = hashlib.md5(user_input[CONF_UID].encode("utf-8")).hexdigest()
        await self.async_set_unique_id(uid_md5)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="",
            data=user_input,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for bemfa."""

    _config_entry: config_entries.ConfigEntry
    _topic_map: dict[str, tuple[str, str | None]]

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    # We guide one to sellect entities he wants to sync to bemfa service.
    # Then we make http calls to submit his selection.
    # When reconfiguring, entities selected last time will be checked by default.
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        service = self._get_service()

        # select entities
        entities = service.get_supported_entities()
        self._topic_map = await service.fetch_synced_data_from_server()

        return self.async_show_form(
            step_id="entities",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INCLUDE_ENTITIES,
                        default=[
                            item[1]
                            for item in filter(
                                lambda item: item[1] is not None,
                                self._topic_map.values(),
                            )
                        ],
                    ): cv.multi_select(
                        {entity.entity_id: entity.name for entity in entities}
                    ),
                }
            ),
            last_step=True,
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Sync selected entities to bemfa service."""
        service = self._get_service()

        current_entities: dict(str, tuple(str, str)) = {}
        for (topic, (name, entity_id)) in self._topic_map.items():
            if entity_id is None:
                # remove unused topics
                await service.remove_topic(topic)
            else:
                current_entities[entity_id] = (topic, name)

        current_entity_ids = set(current_entities.keys())
        new_entity_ids = set(user_input[CONF_INCLUDE_ENTITIES])

        # removed entites
        for entity_id in current_entity_ids - new_entity_ids:
            await service.remove_topic(current_entities[entity_id][0])

        # renamed entities?
        for entity_id in current_entity_ids & new_entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            if state.name != current_entities[entity_id][1]:
                await service.rename_topic(current_entities[entity_id][0], state.name)

        # added entities
        for entity_id in new_entity_ids - current_entity_ids:
            await service.add_topic(entity_id)
        # end to sync

        return self.async_create_entry(
            data=user_input,
        )

    def _get_service(self) -> BemfaService:
        return self.hass.data[DOMAIN].get(self._config_entry.entry_id)["service"]
