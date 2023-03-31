"""Support for bemfa service."""
from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Any
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN, STATE_IDLE
from homeassistant.components.group import DOMAIN as GROUP_DOMAIN
from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.siren import DOMAIN as SIREN_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.vacuum import (
    DOMAIN as VACUUM_DOMAIN,
    SERVICE_RETURN_TO_BASE,
    SERVICE_START,
    SERVICE_STOP,
    STATE_CLEANING,
    VacuumEntityFeature,
)
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_UNLOCK,
    SERVICE_LOCK,
    STATE_LOCKED,
    STATE_ON,
    STATE_PLAYING,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.util.read_only_dict import ReadOnlyDict
from .const import MSG_OFF, MSG_ON, TopicSuffix
from .sync import SYNC_TYPES, ControllableSync


@SYNC_TYPES.register("switch")
class Switch(ControllableSync):
    """Many domains which bemfa do not support need to be converted to switch."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_switch"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.SWITCH

    @staticmethod
    def _supported_domain() -> list[str]:
        return [
            SWITCH_DOMAIN,
            SCRIPT_DOMAIN,
            INPUT_BOOLEAN_DOMAIN,
            AUTOMATION_DOMAIN,
            HUMIDIFIER_DOMAIN,
            REMOTE_DOMAIN,
            SIREN_DOMAIN,
        ]

    def _msg_generators(
        self,
    ) -> list[Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]]:
        return [self._msg_generator()]

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
                # split bemfa msg by "#", then take a sub list
                0,  # from this index
                1,  # to this index
                lambda msg, attributes: (  # and pass to this fun as param "msg"
                    self._service_domain(),
                    self._service_names()[0]
                    if msg[0] == MSG_ON
                    else self._service_names()[1],
                    {},
                ),
            )
        ]

    def _msg_generator(
        self,
    ) -> Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]:
        return lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF

    def _service_domain(self) -> str:
        """Domain of service calls."""
        return self._entity_id.split(".")[0]

    def _service_names(self) -> tuple[str, str]:
        """On/off services to call."""
        return (SERVICE_TURN_ON, SERVICE_TURN_OFF)


@SYNC_TYPES.register("camera")
class Camera(Switch):
    """Sync a hass camera entity to bemfa switch device."""

    @staticmethod
    def _supported_domain() -> str:
        return CAMERA_DOMAIN

    def _msg_generator(
        self,
    ) -> Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]:
        return lambda state, attributes: MSG_OFF if state == STATE_IDLE else MSG_ON


@SYNC_TYPES.register("media_player")
class MediaPlayer(Switch):
    """Sync a hass media player entity to bemfa switch device."""

    @staticmethod
    def _supported_domain() -> str:
        return MEDIA_PLAYER_DOMAIN

    def _msg_generator(
        self,
    ) -> Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]:
        return lambda state, attributes: MSG_ON if state == STATE_PLAYING else MSG_OFF


@SYNC_TYPES.register("lock")
class Lock(Switch):
    """Sync a hass lock entity to bemfa switch device."""

    @staticmethod
    def _supported_domain() -> str:
        return LOCK_DOMAIN

    def _msg_generator(
        self,
    ) -> Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]:
        return lambda state, attributes: MSG_OFF if state == STATE_LOCKED else MSG_ON

    def _service_names(self) -> tuple[str, str]:
        return (SERVICE_UNLOCK, SERVICE_LOCK)


@SYNC_TYPES.register("scene")
class Scene(Switch):
    """Treat state of SCENE as always OFF to triggle it at any time."""

    @staticmethod
    def _supported_domain() -> str:
        return SCENE_DOMAIN

    def _msg_generator(
        self,
    ) -> Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]:
        return lambda state, attributes: MSG_OFF


@SYNC_TYPES.register("group")
class Group(Switch):
    """Service domain for old style GROUP is homeassistant."""

    @staticmethod
    def _supported_domain() -> str:
        return GROUP_DOMAIN

    def _service_domain(self) -> str:
        return HOMEASSISTANT_DOMAIN


@SYNC_TYPES.register("vacuum")
class Vacuum(Switch):
    """Sync a hass vacuum entity to bemfa switch device."""

    @staticmethod
    def _supported_domain() -> str:
        return VACUUM_DOMAIN

    def _msg_generator(
        self,
    ) -> Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]:
        return (
            lambda state, attributes: MSG_ON
            if state in [STATE_ON, STATE_CLEANING]
            else MSG_OFF
        )

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
                1,
                lambda msg, attributes: (
                    VACUUM_DOMAIN,
                    SERVICE_START
                    if msg[0] == MSG_ON
                    and attributes[ATTR_SUPPORTED_FEATURES] & VacuumEntityFeature.START
                    else SERVICE_TURN_ON
                    if msg[0] == MSG_ON
                    else SERVICE_RETURN_TO_BASE
                    if msg[0] == MSG_OFF
                    and attributes[ATTR_SUPPORTED_FEATURES]
                    & VacuumEntityFeature.RETURN_HOME
                    else SERVICE_STOP
                    if msg[0] == MSG_OFF
                    and attributes[ATTR_SUPPORTED_FEATURES] & VacuumEntityFeature.STOP
                    else SERVICE_TURN_OFF,
                    {},
                ),
            )
        ]
