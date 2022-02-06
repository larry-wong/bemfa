"""Constants for the bemfa integration."""

from typing import Final

DOMAIN: Final = "bemfa"

# #### Config ####
CONF_UID = "uid"
CONF_INCLUDE_ENTITIES: Final = "include_entities"

# #### MQTT ####
MQTT_HOST: Final = "bemfa.com"
MQTT_PORT: Final = 9501
MQTT_KEEPALIVE: Final = 600
TOPIC_PUBLISH: Final = "{topic}/set"
TOPIC_PREFIX: Final = "hass"
TOPIC_SUFFIX_LIGHT: Final = "002"
TOPIC_SUFFIX_FAN: Final = "003"
TOPIC_SUFFIX_SENSOR: Final = "004"
TOPIC_SUFFIX_CLIMATE: Final = "005"
TOPIC_SUFFIX_SWITCH: Final = "006"
TOPIC_SUFFIX_COVER: Final = "009"
TOPIC_PING: Final = f"{TOPIC_PREFIX}ping"
INTERVAL_PING = 30  # send ping msg evry 30s
INTERVAL_NO_PING = 100  # reconnect to mqtt server in 100s without ping msg received
MSG_SEPARATOR: Final = "#"
MSG_ON: Final = "on"
MSG_OFF: Final = "off"
MSG_PAUSE: Final = "pause"  # for covers
MSG_SPEED_COUNT: Final = 4  # for fans, 4 speed supported at most

# #### Service Api ####
HTTP_BASE_URL: Final = f"https://api.{MQTT_HOST}/api/"
FETCH_TOPICS_URL: Final = "https://api.bemfa.com/api/device/v1/topic/?uid={uid}&type=2"
ADD_TOPIC_URL: Final = f"{HTTP_BASE_URL}user/addtopic/"
RENAME_TOPIC_URL: Final = f"{HTTP_BASE_URL}device/v1/topic/name/"
DEL_TOPIC_URL: Final = f"{HTTP_BASE_URL}user/deltopic/"
