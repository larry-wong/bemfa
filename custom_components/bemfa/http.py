"""Bemfa http apis."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CREATE_TOPIC_URL,
    DEL_TOPIC_URL,
    FETCH_TOPICS_URL,
    RENAME_TOPIC_URL,
    TOPIC_PREFIX,
)

_LOGGING = logging.getLogger(__name__)


class BemfaHttp:
    """Send http requests to bemfa service."""

    def __init__(self, hass: HomeAssistant, uid: str) -> None:
        """Initialize."""
        self._hass = hass
        self._uid = uid

    async def async_fetch_all_topics(self) -> dict[str, str]:
        """Fetch all topics created by us from bemfa service."""
        session = async_get_clientsession(self._hass)
        async with session.get(
            FETCH_TOPICS_URL.format(uid=self._uid),
        ) as res:
            res.raise_for_status()
            res_dict = await res.json(content_type="application/json", encoding="utf-8")
            if res_dict["code"] == 0 and res_dict["message"] == "OK" and res_dict["data"] is not None:
                return {
                    topic["topic"]: topic["name"]
                    for topic in res_dict["data"]
                    if topic["topic"].startswith(TOPIC_PREFIX)
                }
            return {}

    async def async_create_topic(self, topic: str, name: str) -> None:
        """Create a topic to bemfa service."""
        if not topic.startswith(TOPIC_PREFIX):
            return
        session = async_get_clientsession(self._hass)
        await session.post(
            CREATE_TOPIC_URL,
            data={
                "uid": self._uid,
                "topic": topic,
                "type": 1,
                "name": name,
            },
        )

    async def async_rename_topic(self, topic: str, name: str) -> None:
        """Rename a topic in bemfa service."""
        if not topic.startswith(TOPIC_PREFIX):
            return
        session = async_get_clientsession(self._hass)
        await session.post(
            RENAME_TOPIC_URL,
            data={
                "uid": self._uid,
                "topic": topic,
                "type": 1,
                "name": name,
            },
        )

    async def async_del_topic(self, topic: str) -> None:
        """Delete a topic from bemfa service."""
        if not topic.startswith(TOPIC_PREFIX):
            return
        session = async_get_clientsession(self._hass)
        await session.post(
            DEL_TOPIC_URL,
            data={
                "uid": self._uid,
                "topic": topic,
                "type": 1,
            },
        )
