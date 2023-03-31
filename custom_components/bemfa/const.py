"""Constants for the bemfa integration."""

from typing import Final

from homeassistant.backports.enum import StrEnum

DOMAIN: Final = "bemfa"

# #### Config ####
CONF_UID: Final = "uid"

OPTIONS_CONFIG: Final = "config"
OPTIONS_SELECT: Final = "select"
OPTIONS_NAME: Final = "name"
OPTIONS_TEMPERATURE: Final = "temperature"
OPTIONS_HUMIDITY: Final = "humidity"
OPTIONS_ILLUMINANCE: Final = "illuminance"
OPTIONS_PM25: Final = "pm25"
OPTIONS_CO2: Final = "co2"

# #### MQTT ####
class TopicSuffix(StrEnum):
    """Suffix for bemfa MQTT topic"""

    LIGHT = "002"
    FAN = "003"
    SENSOR = "004"
    CLIMATE = "005"
    SWITCH = "006"
    COVER = "009"


MQTT_HOST: Final = "bemfa.com"
MQTT_PORT: Final = 9501
MQTT_KEEPALIVE: Final = 600
TOPIC_PUBLISH: Final = "{topic}/set"
TOPIC_PREFIX: Final = "hass"
TOPIC_PING: Final = f"{TOPIC_PREFIX}ping"
INTERVAL_PING_SEND = 30  # send ping msg every 30s
INTERVAL_PING_RECEIVE = 20  # detect a ping lost in 20s after a ping message send
MAX_PING_LOST = 3  # reconnect to mqtt server when 3 continous ping losts detected
MSG_SEPARATOR: Final = "#"
MSG_ON: Final = "on"
MSG_OFF: Final = "off"
MSG_PAUSE: Final = "pause"  # for covers
MSG_SPEED_COUNT: Final = 4  # for fans, 4 speed supported at most

# #### Service Api ####
HTTP_BASE_URL: Final = f"https://api.{MQTT_HOST}/api/"
FETCH_TOPICS_URL: Final = "https://api.bemfa.com/api/device/v1/topic/?uid={uid}&type=2"
CREATE_TOPIC_URL: Final = f"{HTTP_BASE_URL}user/addtopic/"
RENAME_TOPIC_URL: Final = f"{HTTP_BASE_URL}device/v1/topic/name/"
DEL_TOPIC_URL: Final = f"{HTTP_BASE_URL}user/deltopic/"
