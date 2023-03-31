"""Support for bemfa service."""


from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import DOMAIN
from .const import MSG_OFF, MSG_ON, TopicSuffix
from .sync import SYNC_TYPES, Sync


@SYNC_TYPES.register("binary_sensor")
class BinarySensor(Sync):
    """Sync a hass binary sensor entity to bemfa sensor device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_binary_sensor"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.SENSOR

    @classmethod
    def collect_supported_syncs(cls, hass: HomeAssistant):
        return [
            cls(hass, state.entity_id, state.name)
            for state in hass.states.async_all(DOMAIN)
        ]

    def get_watched_entity_ids(self) -> list[str]:
        return [self._entity_id]

    def _generate_msg_parts(self) -> list[str]:
        state = self._hass.states.get(self._entity_id)
        if state is None:
            return []

        return ["", "", "", MSG_ON if state.state == STATE_ON else MSG_OFF]
