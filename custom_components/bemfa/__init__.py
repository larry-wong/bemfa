"""The bemfa integration."""
from __future__ import annotations

import hashlib
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_INCLUDE_ENTITIES, CONF_UID, DOMAIN
from .mqtt import BemfaMqtt
from .service import BemfaService

_LOGGING = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up bemfa from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    service = BemfaService(hass, entry.data.get(CONF_UID))
    await service.start()

    hass.data[DOMAIN][entry.entry_id] = {
        "service": service,
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data is not None:
        data["service"].stop()
        hass.data[DOMAIN].pop(entry.entry_id)

    return True
