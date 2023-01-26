"""Support for bemfa service."""
from __future__ import annotations
import asyncio

import logging
from typing import Any

import paho.mqtt.client as mqtt

from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import HomeAssistant

from .const import (
    INTERVAL_PING_RECEIVE,
    INTERVAL_PING_SEND,
    MAX_PING_LOST,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    TOPIC_PING,
    TOPIC_PUBLISH,
)
from .helper import (
    generate_msg,
    generate_msg_list,
    resolve_msg,
)

_LOGGING = logging.getLogger(__name__)


class BemfaMqtt:
    """Set up mqtt connections to bemfa service, subscribe topcs and publish messages."""

    _topic_to_entity_id: dict[str, str] = {}
    _remove_listener: Any = None
    _ping_publish_timer: Any = None
    _ping_receive_timer: Any = None
    _ping_lost: int = 0

    def __init__(
        self, hass: HomeAssistant, uid: str, entity_ids: list[str] | None
    ) -> None:
        """Initialize."""
        self._hass = hass

        # Init MQTT connection
        self._mqttc = mqtt.Client(uid, mqtt.MQTTv311)

    def update_topics(self, topic_to_entity_id: dict[str, str]):
        """Update topics we are watching."""
        current_topics = set(self._topic_to_entity_id.keys())
        new_topics = set(topic_to_entity_id.keys())
        for topic in current_topics - new_topics:
            self.remove_topic(topic)

        for topic in new_topics - current_topics:
            self.add_topic(topic, topic_to_entity_id[topic])

    def add_topic(self, topic: str, entity_id: str):
        """Add an topic to our watching list"""
        state = self._hass.states.get(entity_id)
        if state is None:
            return
        self._topic_to_entity_id[topic] = entity_id
        self._mqttc.publish(
            TOPIC_PUBLISH.format(topic=topic),
            generate_msg(state.domain, state.state, state.attributes),
        )
        self._mqttc.subscribe(topic, 2)

    def remove_topic(self, topic: str):
        """Remove an topic from our watching list"""
        if topic in self._topic_to_entity_id:
            self._topic_to_entity_id.pop(topic)
        self._mqttc.unsubscribe(topic)

    def connect(self) -> None:
        """Connect to Bamfa service."""
        # Send heartbeat packages to check the connection first in case we failed to make mqtt connection
        self._ping()

        self._mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
        self._mqttc.on_message = self._mqtt_on_message

        self._mqttc.loop_start()

        # Listen for state changes
        self._remove_listener = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._state_listener
        )

        # Listen for heartbeat packages
        self._mqttc.subscribe(TOPIC_PING, 2)

    def _ping(self):
        async def _receive_job():
            await asyncio.sleep(INTERVAL_PING_RECEIVE)
            self._ping_lost += 1
            if self._ping_lost == MAX_PING_LOST:
                self._reconnect()
                self._ping_lost = 0

        async def _publish_job():
            await asyncio.sleep(INTERVAL_PING_SEND)
            self._mqttc.publish(TOPIC_PING, "ping")
            self._ping_receive_timer = asyncio.ensure_future(_receive_job())
            self._ping()

        self._ping_publish_timer = asyncio.ensure_future(_publish_job())

    def _reconnect(self):
        topic_to_entity_id = self._topic_to_entity_id.copy()
        self.disconnect()
        self.connect()
        self.update_topics(topic_to_entity_id)

    def disconnect(self) -> None:
        """Disconnect from Bamfa service."""

        # Remove timers
        if self._ping_publish_timer is not None:
            self._ping_publish_timer.cancel()
        if self._ping_receive_timer is not None:
            self._ping_receive_timer.cancel()

        # Unlisten for state changes
        if self._remove_listener is not None:
            self._remove_listener()

        # Destroy MQTT connection
        self._mqttc.loop_stop()
        self._mqttc.disconnect()

        # data clean
        self._topic_to_entity_id.clear()

    def _state_listener(self, event):
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        entity_id = new_state.entity_id
        topic = self._get_topic_by_entity_id(entity_id)
        if topic is None:
            return
        state = self._hass.states.get(entity_id)
        self._mqttc.publish(
            TOPIC_PUBLISH.format(topic=topic),
            generate_msg(state.domain, state.state, state.attributes),
        )

    def _get_topic_by_entity_id(self, entity_id: str) -> str | None:
        if entity_id not in self._topic_to_entity_id.values():
            return None
        return (list(self._topic_to_entity_id.keys()))[
            list(self._topic_to_entity_id.values()).index(entity_id)
        ]

    def _mqtt_on_message(self, _mqtt_client, _userdata, message) -> None:
        if message.topic == TOPIC_PING:
            if self._ping_receive_timer is not None:
                self._ping_receive_timer.cancel()
                self._ping_lost = 0
            return

        entity_id = self._topic_to_entity_id[message.topic]
        state = self._hass.states.get(entity_id)
        if state is None:
            return
        (msg_list, actions) = resolve_msg(
            state.domain, message.payload.decode(), state.attributes
        )

        # generate msg from entity to compare to received msg
        my_msg_list = generate_msg_list(state.domain, state.state, state.attributes)
        for action in actions:
            start_index = action[0]
            end_index = min(action[1], len(msg_list), len(my_msg_list))
            if msg_list[start_index:end_index] != my_msg_list[start_index:end_index]:
                data = {ATTR_ENTITY_ID: entity_id}
                if action[4] is not None:
                    data.update(action[4])
                self._hass.services.call(
                    domain=action[2], service=action[3], service_data=data
                )
                break  # call only one service on each msg received
