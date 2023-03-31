"""Support for bemfa service."""
from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Any
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
    DOMAIN,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.util.read_only_dict import ReadOnlyDict
from .const import MSG_OFF, MSG_ON, TopicSuffix
from .utils import has_key
from .sync import SYNC_TYPES, ControllableSync

SUPPORTED_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.FAN_ONLY,
    HVACMode.DRY,
]


@SYNC_TYPES.register("climate")
class Climate(ControllableSync):
    """Sync a hass climate entity to bemfa climate device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_climate"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.CLIMATE

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _msg_generators(
        self,
    ) -> list[Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]]:
        return [
            lambda state, attributes: MSG_OFF if state == HVACMode.OFF else MSG_ON,
            lambda state, attributes: SUPPORTED_HVAC_MODES.index(state) + 1
            if state in SUPPORTED_HVAC_MODES
            else "",
            lambda state, attributes: round(attributes[ATTR_TEMPERATURE])
            if has_key(attributes, ATTR_TEMPERATURE)
            else "",
        ]

    def _msg_resolvers(
        self,
    ) -> list[
        (
            int,
            int,
            Callable[
                [list[str | int], ReadOnlyDict[Mapping[str, Any]]],
                (str, str, dict[str, Any]),
            ],
        )
    ]:
        return [
            (
                0,
                2,
                lambda msg, attributes: (
                    DOMAIN,
                    SERVICE_SET_HVAC_MODE,
                    {ATTR_HVAC_MODE: SUPPORTED_HVAC_MODES[msg[1] - 1]},
                )
                if len(msg) > 1 and msg[1] >= 1 and msg[1] <= 5
                else (DOMAIN, SERVICE_TURN_ON, {})
                if msg[0] == MSG_ON and len(msg) == 1
                else (DOMAIN, SERVICE_TURN_OFF, {}),
            ),
            (
                2,
                3,
                lambda msg, attributes: (
                    DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {ATTR_TEMPERATURE: msg[0]},
                ),
            ),
        ]
