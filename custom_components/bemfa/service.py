"""Support for bemfa service."""
from __future__ import annotations

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, State
from .const import TOPIC_PING
from .http import BemfaHttp
from .mqtt import BemfaMqtt
from .entities_config import ENTITIES_CONFIG, FILTER
from .helper import generate_topic

_LOGGING = logging.getLogger(__name__)


class BemfaService:
    """Service handles mqtt topocs and connection."""

    _hass: HomeAssistant
    _bemfa_http: BemfaHttp
    _bemfa_mqtt: BemfaMqtt

    def __init__(self, hass: HomeAssistant, uid: str) -> None:
        """Initialize."""
        self._hass = hass
        self._bemfa_http = BemfaHttp(hass, uid)
        self._bemfa_mqtt = BemfaMqtt(hass, uid, None)

    async def start(self) -> None:
        """Start the servcie, called when Bemfa component starts."""
        all_topics = await self._bemfa_http.async_fetch_all_topics()

        # make sure we have the ping topic for heartbeat packages
        if TOPIC_PING not in all_topics:
            await self._bemfa_http.async_add_topic(TOPIC_PING, "ping")
        else:
            # This topic does not matter to entities, remove it for following steps
            del all_topics[TOPIC_PING]

        # time to make mqtt connection
        self._bemfa_mqtt.connect()

        # When sync an entity to bemfa service,
        # we must make sure this entity's state is available, means this entity has inited.
        # So a check of hass state is necessary.
        def _start(event: Event | None = None):
            topic_to_entity_id: dict[str, str] = {}
            for entity in self._hass.states.async_all(ENTITIES_CONFIG.keys()):
                topic = generate_topic(entity.domain, entity.entity_id)
                if topic in all_topics:
                    topic_to_entity_id[topic] = entity.entity_id
            self._bemfa_mqtt.update_topics(topic_to_entity_id)

        if self._hass.state == CoreState.running:
            _start()
        else:
            # for situations when hass restarts
            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _start)

    async def fetch_synced_data_from_server(
        self,
    ) -> dict[str, tuple[str, str | None]]:  # topic -> [name, entity_id | None]
        """Fetch data we've synchronized to bemfa service."""
        all_topics = await self._bemfa_http.async_fetch_all_topics()

        # find corresponding entities
        topic_map: dict[str, str] = {}
        for entity in self._hass.states.async_all(ENTITIES_CONFIG.keys()):
            topic = generate_topic(entity.domain, entity.entity_id)
            if topic in all_topics:
                topic_map[topic] = (all_topics[topic], entity.entity_id)
                del all_topics[topic]

        if TOPIC_PING in all_topics:
            del all_topics[TOPIC_PING]

        for (topic, name) in all_topics.items():
            topic_map[topic] = (name, None)

        return topic_map

    def get_supported_entities(self) -> list[State]:
        """Filter entities we support."""
        entities = sorted(
            filter(
                lambda item: FILTER not in ENTITIES_CONFIG[item.domain]
                or ENTITIES_CONFIG[item.domain][FILTER](item.attributes),
                self._hass.states.async_all(ENTITIES_CONFIG.keys()),
            ),
            key=lambda item: item.entity_id,
        )
        return entities

    async def add_topic(self, entity_id: str, name: str):
        """Sync an topic to bemfa service"""
        state = self._hass.states.get(entity_id)
        if state is None:
            return
        topic = generate_topic(state.domain, entity_id)
        await self._bemfa_http.async_add_topic(topic, name)
        self._bemfa_mqtt.add_topic(topic, entity_id)

    async def rename_topic(self, topic: str, name: str):
        """Rename a topic to Bemfa Servcie"""
        await self._bemfa_http.async_rename_topic(topic, name)

    async def remove_topic(self, topic):
        """Unsync an topic from bemfa service"""
        await self._bemfa_http.async_del_topic(topic)
        self._bemfa_mqtt.remove_topic(topic)

    def stop(self) -> None:
        """Stop the service, called when Bemfa component stops."""
        self._bemfa_mqtt.disconnect()
