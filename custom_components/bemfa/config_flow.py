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

from .const import (
    CONF_UID,
    DOMAIN,
    OPTIONS_NAME,
    OPTIONS_OPERATION,
    OPTIONS_SELECT,
    Operation,
)
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
    _user_input: dict[str, str] = {}

    # a dict to hold id/topic_2_name mapping when add / modify a sync
    # with this map we can get default name in next step
    _name_dict: dict[str, str] = {}

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_sync", "modify_sync", "remove_sync"],
        )

    async def async_step_add_sync(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Sync a hass entity to bemfa service"""
        if user_input is not None:
            return await self.async_step_set_sync_name(user_input)

        service = self._get_service()
        all_entities = service.get_supported_entities()
        topic_map = await service.fetch_synced_data_from_server()
        synced_entity_ids = set(
            [
                item[1]
                for item in filter(lambda item: item[1] is not None, topic_map.values())
            ]
        )

        # filter out unsynced entities
        self._name_dict.clear()
        for entity in filter(
            lambda entity: entity.entity_id not in synced_entity_ids, all_entities
        ):
            self._name_dict[entity.entity_id] = entity.name

        self._user_input[OPTIONS_OPERATION] = Operation.ADD

        return self.async_show_form(
            step_id="add_sync",
            data_schema=vol.Schema(
                {
                    vol.Required(OPTIONS_SELECT): vol.In(
                        {
                            entity_id: name + " (" + entity_id + ")"
                            for (entity_id, name) in self._name_dict.items()
                        }
                    )
                }
            ),
            last_step=False,
        )

    async def async_step_modify_sync(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Modify a hass-to-bemfa sync"""
        if user_input is not None:
            return await self.async_step_set_sync_name(user_input)

        service = self._get_service()
        topic_map = await service.fetch_synced_data_from_server()

        # filter out synced entities
        self._name_dict.clear()
        topic_id_dict: dict[str, str] = {}
        for (topic, [name, entity_id]) in topic_map.items():
            if entity_id is not None:
                self._name_dict[topic] = name
                topic_id_dict[topic] = entity_id

        self._user_input[OPTIONS_OPERATION] = Operation.MODIFY

        return self.async_show_form(
            step_id="modify_sync",
            data_schema=vol.Schema(
                {
                    vol.Required(OPTIONS_SELECT): vol.In(
                        {
                            topic: name + " (" + topic_id_dict[topic] + ")"
                            for (topic, name) in self._name_dict.items()
                        }
                    )
                }
            ),
            last_step=False,
        )

    async def async_step_remove_sync(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove hass-to-bemfa sync(s)"""
        if user_input is not None:
            service = self._get_service()
            for topic in user_input[OPTIONS_SELECT]:
                await service.remove_topic(topic)
            self._user_input.clear()
            return self.async_create_entry(title="", data=None)

        service = self._get_service()
        topic_map = await service.fetch_synced_data_from_server()

        return self.async_show_form(
            step_id="remove_sync",
            data_schema=vol.Schema(
                {
                    vol.Required(OPTIONS_SELECT): cv.multi_select(
                        {
                            topic: name
                            + (" (" + entity_id + ")" if entity_id is not None else "")
                            for (topic, [name, entity_id]) in topic_map.items()
                        }
                    )
                }
            ),
            last_step=False,
        )

    async def async_step_set_sync_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set details of a sync"""
        self._user_input.update(user_input)
        if OPTIONS_NAME in self._user_input:
            service = self._get_service()
            if self._user_input[OPTIONS_OPERATION] == Operation.ADD:
                await service.add_topic(
                    self._user_input[OPTIONS_SELECT],
                    self._user_input[OPTIONS_NAME],
                )
            else:
                await service.rename_topic(
                    self._user_input[OPTIONS_SELECT],
                    self._user_input[OPTIONS_NAME],
                )
            self._user_input.clear()
            self._name_dict.clear()
            return self.async_create_entry(title="", data=None)

        return self.async_show_form(
            step_id="set_sync_name",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPTIONS_NAME,
                        default=self._name_dict[self._user_input[OPTIONS_SELECT]],
                    ): str
                }
            ),
        )

    def _get_service(self) -> BemfaService:
        return self.hass.data[DOMAIN].get(self._config_entry.entry_id)["service"]
