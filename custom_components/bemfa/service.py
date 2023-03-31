"""Support for bemfa service."""
from __future__ import annotations

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant
from .sync import SYNC_TYPES, Sync
from .const import OPTIONS_NAME, TOPIC_PING
from .http import BemfaHttp
from .mqtt import BemfaMqtt

_LOGGING = logging.getLogger(__name__)


class BemfaService:
    """Service handles mqtt topocs and connection."""

    def __init__(self, hass: HomeAssistant, uid: str) -> None:
        """Initialize."""
        self._hass = hass
        self._bemfa_http = BemfaHttp(hass, uid)
        self._bemfa_mqtt = BemfaMqtt(hass, uid, None)

    async def async_start(self, config: dict[str, dict[str, str]]) -> None:
        """Start the servcie, called when Bemfa component starts."""
        all_topics = await self._bemfa_http.async_fetch_all_topics()

        # make sure we have the ping topic for heartbeat packages
        if TOPIC_PING not in all_topics:
            await self._bemfa_http.async_create_topic(TOPIC_PING, "ping")
        else:
            # This topic does not matter to entities, remove it for following steps
            del all_topics[TOPIC_PING]

        # time to make mqtt connection
        self._bemfa_mqtt.connect()

        # When sync an entity to bemfa service,
        # we must make sure this entity's state is available, means this entity has inited.
        # So a check of hass state is necessary.
        def _start(event: Event | None = None):
            for sync in self.collect_supported_syncs():
                if sync.topic in all_topics:
                    sync.name = all_topics[sync.topic]
                    if sync.topic in config:
                        sync.config = config[sync.topic]
                    self._bemfa_mqtt.create_sync(sync)

        if self._hass.state == CoreState.running:
            _start()
        else:
            # for situations when hass restarts
            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _start)

    async def async_fetch_all_topics(
        self,
    ) -> dict[str, str]:  # topic -> name
        """Fetch topics we created from benfa servcie, include which do not exist in hass."""
        all_topics = await self._bemfa_http.async_fetch_all_topics()

        if TOPIC_PING in all_topics:
            del all_topics[TOPIC_PING]

        return all_topics

    def collect_supported_syncs(self) -> list[Sync]:
        """Collect all supported hass-to-bemfa syncs."""
        syncs: list[Sync] = []
        for sync_type in SYNC_TYPES.values():
            syncs.extend(sync_type.collect_supported_syncs(self._hass))
        return sorted(syncs, key=lambda item: item.entity_id)

    async def async_create_sync(self, sync: Sync, user_input: dict[str, str]):
        """Create a topic to bemfa service and keep communication by mqtt.
        Except name, we store other config details in hass side.
        """
        sync.name = user_input.pop(OPTIONS_NAME)
        sync.config = user_input
        await self._bemfa_http.async_create_topic(sync.topic, sync.name)
        self._bemfa_mqtt.create_sync(sync)

    async def async_modify_sync(self, sync: Sync, user_input: dict[str, str]):
        """Modify topic and/or config of a sync."""
        name = user_input.pop(OPTIONS_NAME)
        if sync.name != name:
            sync.name = name
            await self._bemfa_http.async_rename_topic(sync.topic, name)
        if sync.config != user_input:
            sync.config = user_input
            self._bemfa_mqtt.modify_sync(sync)

    async def async_destroy_sync(self, topic: str):
        """Delete a topic from bemfa service and distroy mqtt communication."""
        await self._bemfa_http.async_del_topic(topic)
        self._bemfa_mqtt.destroy_sync(topic)

    def stop(self) -> None:
        """Stop the service, called when Bemfa component stops."""
        self._bemfa_mqtt.disconnect()
