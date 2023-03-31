"""Support for bemfa service."""

import logging
from typing import Any
import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry
from homeassistant.helpers.template import area_entities
from .utils import has_key
from .const import (
    OPTIONS_CO2,
    OPTIONS_HUMIDITY,
    OPTIONS_ILLUMINANCE,
    OPTIONS_PM25,
    OPTIONS_TEMPERATURE,
    TopicSuffix,
)
from .sync import SYNC_TYPES, Sync

_LOGGING = logging.getLogger(__name__)


@SYNC_TYPES.register("sensor")
class Sensor(Sync):
    """Sync a hass area to bemfa sensor device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_sensor"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.SENSOR

    @classmethod
    def collect_supported_syncs(cls, hass: HomeAssistant):
        """Group hass sensors by area. Each area maps a bemfa sensor device."""
        return [
            cls(hass, "area.{id}".format(id=area.id), area.name)
            for area in area_registry.async_get(hass).async_list_areas()
        ]

    def generate_details_schema(self) -> dict[str, Any]:
        temperature_sensors: dict[str, str] = {}
        humidity_sensors: dict[str, str] = {}
        illuminance_sensors: dict[str, str] = {}
        pm25_sensors: dict[str, str] = {}
        co2_sensors: dict[str, str] = {}

        # filter entities in our area
        a_entities = area_entities(self._hass, self._entity_id.split(".")[1])

        for state in self._hass.states.async_all(SENSOR_DOMAIN):
            if state.entity_id not in a_entities:
                continue
            if not has_key(state.attributes, ATTR_DEVICE_CLASS):
                continue
            for (_d, _c) in (
                (temperature_sensors, SensorDeviceClass.TEMPERATURE),
                (humidity_sensors, SensorDeviceClass.HUMIDITY),
                (illuminance_sensors, SensorDeviceClass.ILLUMINANCE),
                (pm25_sensors, SensorDeviceClass.PM25),
                (co2_sensors, SensorDeviceClass.CO2),
            ):
                if state.attributes[ATTR_DEVICE_CLASS] == _c:
                    _d[state.entity_id] = "{name}({id})".format(
                        name=state.name, id=state.entity_id
                    )
                    break
        schema = super().generate_details_schema()
        for (_t, _d) in (
            (OPTIONS_TEMPERATURE, temperature_sensors),
            (OPTIONS_HUMIDITY, humidity_sensors),
            (OPTIONS_ILLUMINANCE, illuminance_sensors),
            (OPTIONS_PM25, pm25_sensors),
            (OPTIONS_CO2, co2_sensors),
        ):
            if _d:
                schema[
                    vol.Optional(
                        _t,
                        default=self._config[_t]
                        if _t in self._config and self._config[_t] in _d
                        else list(_d.keys())[0],
                    )
                ] = vol.In(_d)
        return schema

    def get_watched_entity_ids(self) -> list[str]:
        ids: list[str] = []
        for name in (
            OPTIONS_TEMPERATURE,
            OPTIONS_HUMIDITY,
            OPTIONS_ILLUMINANCE,
            OPTIONS_PM25,
            OPTIONS_CO2,
        ):
            if name in self._config:
                ids.append(self._config[name])
        return ids

    def _generate_msg_parts(self) -> list[str]:
        msg: list[str] = [""]
        for name in (
            OPTIONS_TEMPERATURE,
            OPTIONS_HUMIDITY,
            "",
            OPTIONS_ILLUMINANCE,
            OPTIONS_PM25,
            OPTIONS_CO2,
        ):
            if name in self._config:
                state = self._hass.states.get(self._config[name])
                if state is not None:
                    msg.append(state.state)
        return msg
