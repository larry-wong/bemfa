"""Support for bemfa service."""
from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Any
from homeassistant.components.fan import (
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    DOMAIN,
    SERVICE_OSCILLATE,
    SERVICE_SET_PERCENTAGE,
)
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON
from homeassistant.util.read_only_dict import ReadOnlyDict
from .const import MSG_OFF, MSG_ON, TopicSuffix
from .utils import has_key
from .sync import SYNC_TYPES, ControllableSync


@SYNC_TYPES.register("fan")
class Fan(ControllableSync):
    """Sync a hass fan entity to bemfa fan device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_fan"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.FAN

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _msg_generators(
        self,
    ) -> list[Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]]:
        return [
            lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF,
            lambda state, attributes: min(
                round(attributes[ATTR_PERCENTAGE] / attributes[ATTR_PERCENTAGE_STEP]), 4
            )
            if has_key(attributes, ATTR_PERCENTAGE)
            and has_key(attributes, ATTR_PERCENTAGE_STEP)
            else "",
            lambda state, attributes: 1
            if has_key(attributes, ATTR_OSCILLATING) and attributes[ATTR_OSCILLATING]
            else 0
            if has_key(attributes, ATTR_OSCILLATING)
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
                    SERVICE_SET_PERCENTAGE,
                    {
                        ATTR_PERCENTAGE: min(
                            max(msg[1], 1) * attributes[ATTR_PERCENTAGE_STEP], 100
                        )
                    },
                )
                if len(msg) > 1 and has_key(attributes, ATTR_PERCENTAGE_STEP)
                else (
                    DOMAIN,
                    SERVICE_TURN_ON if msg[0] == MSG_ON else SERVICE_TURN_OFF,
                    {},
                ),
            ),
            (
                2,
                3,
                lambda msg, attributes: (
                    DOMAIN,
                    SERVICE_OSCILLATE,
                    {ATTR_OSCILLATING: msg[0] == 1},
                ),
            ),
        ]
