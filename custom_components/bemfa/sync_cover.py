"""Support for bemfa service."""
from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Any
from homeassistant.components.cover import ATTR_CURRENT_POSITION, ATTR_POSITION, DOMAIN

from homeassistant.const import (
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
)
from homeassistant.util.read_only_dict import ReadOnlyDict
from .const import MSG_OFF, MSG_ON, TopicSuffix
from .utils import has_key
from .sync import SYNC_TYPES, ControllableSync


@SYNC_TYPES.register("cover")
class Cover(ControllableSync):
    """Sync a hass cover entity to bemfa cover device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_cover"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.COVER

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _msg_generators(
        self,
    ) -> list[Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]]:
        return [
            lambda state, attributes: MSG_OFF
            if has_key(attributes, ATTR_CURRENT_POSITION)
            and attributes[ATTR_CURRENT_POSITION] == 0
            or not has_key(attributes, ATTR_CURRENT_POSITION)
            and state == "closed"
            else MSG_ON,
            lambda state, attributes: attributes[ATTR_CURRENT_POSITION]
            if has_key(attributes, ATTR_CURRENT_POSITION)
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
                    SERVICE_SET_COVER_POSITION,
                    {ATTR_POSITION: msg[1]},
                )
                if len(msg) > 1
                else (
                    DOMAIN,
                    SERVICE_OPEN_COVER
                    if msg[0] == MSG_ON
                    else SERVICE_CLOSE_COVER
                    if msg[0] == MSG_OFF
                    else SERVICE_STOP_COVER,
                    {},
                ),
            )
        ]
