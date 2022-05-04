"""How bemfa represents HA entities."""
from __future__ import annotations

from typing import Any, Final

from homeassistant.components.automation.const import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINAEY_SENSOR_DOMAIN
from homeassistant.components.camera import STATE_IDLE
from homeassistant.components.camera.const import DOMAIN as CAMERA_DOMAIN
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
)
from homeassistant.components.fan import (
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    DOMAIN as FAN_DOMAIN,
    SERVICE_OSCILLATE,
    SERVICE_SET_PERCENTAGE,
)
from homeassistant.components.group import DOMAIN as GROUP_DOMAIN
from homeassistant.components.humidifier.const import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP,
    ATTR_MAX_MIREDS,
    ATTR_MIN_MIREDS,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    COLOR_MODE_COLOR_TEMP,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.components.script.const import DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.vacuum import (
    DOMAIN as VACUUM_DOMAIN,
    SERVICE_RETURN_TO_BASE,
    SERVICE_START,
    SERVICE_STOP,
    STATE_CLEANING,
    SUPPORT_RETURN_HOME,
    SUPPORT_START,
    SUPPORT_STOP,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    SERVICE_CLOSE_COVER,
    SERVICE_LOCK,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_UNLOCK,
    STATE_LOCKED,
    STATE_ON,
    STATE_PLAYING,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN

from .const import (
    MSG_OFF,
    MSG_ON,
    TOPIC_SUFFIX_CLIMATE,
    TOPIC_SUFFIX_COVER,
    TOPIC_SUFFIX_FAN,
    TOPIC_SUFFIX_LIGHT,
    TOPIC_SUFFIX_SENSOR,
    TOPIC_SUFFIX_SWITCH,
)

SUFFIX: Final = "suffix"
FILTER: Final = "filter"
GENERATE: Final = "generate"
RESOLVE: Final = "resolve"

SUPPORTED_HVAC_MODES = [
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_DRY,
]


def gen_switch_config(
    service_domain=SWITCH_DOMAIN,
    generate=lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF,
    service_on=SERVICE_TURN_ON,
    service_off=SERVICE_TURN_OFF,
) -> Any:
    """Many domains which Bemfa do not support need to be converted to switch. This function makes things easier."""
    return {
        SUFFIX: TOPIC_SUFFIX_SWITCH,
        GENERATE: [generate],
        RESOLVE: [
            (
                # split bemfa msg by "#", then take a sub list
                0,  # from this index
                1,  # to this index
                lambda msg, attributes: (  # and pass to this fun as param "msg"
                    service_domain,
                    service_on if msg[0] == MSG_ON else service_off,
                    None,
                ),
            )
        ],
    }


def has_key(data: Any, key: str) -> bool:
    """Whether data has specific valid key."""
    return key in data and data[key] is not None


ENTITIES_CONFIG: dict[str, Any] = {
    SENSOR_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_SENSOR,
        FILTER: lambda attributes: has_key(attributes, ATTR_DEVICE_CLASS)
        and attributes[ATTR_DEVICE_CLASS]
        in [
            SensorDeviceClass.TEMPERATURE,
            SensorDeviceClass.HUMIDITY,
            SensorDeviceClass.ILLUMINANCE,
            SensorDeviceClass.PM25,
        ],
        GENERATE: [
            lambda state, attributes: "",  # placeholder
            lambda state, attributes: state
            if attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE
            else "",
            lambda state, attributes: state
            if attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.HUMIDITY
            else "",
            lambda state, attributes: "",
            lambda state, attributes: state
            if attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ILLUMINANCE
            else "",
            lambda state, attributes: state
            if attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.PM25
            else "",
        ],
    },
    BINAEY_SENSOR_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_SENSOR,
        GENERATE: [
            lambda state, attributes: "",  # placeholder
            lambda state, attributes: "",
            lambda state, attributes: "",
            lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF,
        ],
    },
    SWITCH_DOMAIN: gen_switch_config(),
    LIGHT_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_LIGHT,
        GENERATE: [
            lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF,
            lambda state, attributes: round(attributes[ATTR_BRIGHTNESS] / 2.55)
            if has_key(attributes, ATTR_BRIGHTNESS)
            else "",
            lambda state, attributes: 1000000 // attributes[ATTR_COLOR_TEMP]
            if has_key(attributes, ATTR_COLOR_TEMP)
            else attributes[ATTR_RGB_COLOR][0] * 256 * 256
            + attributes[ATTR_RGB_COLOR][1] * 256
            + attributes[ATTR_RGB_COLOR][2]
            if has_key(attributes, ATTR_RGB_COLOR)
            else "",
        ],
        RESOLVE: [
            (
                0,
                3,
                lambda msg, attributes: (
                    LIGHT_DOMAIN,
                    SERVICE_TURN_ON if msg[0] == MSG_ON else SERVICE_TURN_OFF,
                    {
                        ATTR_BRIGHTNESS_PCT: msg[1],
                        ATTR_COLOR_TEMP: min(
                            max(1000000 // msg[2], attributes[ATTR_MIN_MIREDS]),
                            attributes[ATTR_MAX_MIREDS],
                        ),
                    }
                    if len(msg) > 2
                    and has_key(attributes, ATTR_SUPPORTED_COLOR_MODES)
                    and COLOR_MODE_COLOR_TEMP in attributes[ATTR_SUPPORTED_COLOR_MODES]
                    else {
                        ATTR_BRIGHTNESS_PCT: msg[1],
                        ATTR_RGB_COLOR: [
                            msg[2] // 256 // 256,
                            msg[2] // 256 % 256,
                            msg[2] % 256,
                        ],
                    }
                    if len(msg) > 2
                    else {ATTR_BRIGHTNESS_PCT: msg[1]}
                    if len(msg) > 1
                    else None,
                ),
            )
        ],
    },
    COVER_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_COVER,
        GENERATE: [
            lambda state, attributes: MSG_OFF
            if has_key(attributes, ATTR_CURRENT_POSITION)
            and attributes[ATTR_CURRENT_POSITION] == 0
            or not has_key(attributes, ATTR_CURRENT_POSITION)
            and state == "closed"
            else MSG_ON,
            lambda state, attributes: attributes[ATTR_CURRENT_POSITION]
            if has_key(attributes, ATTR_CURRENT_POSITION)
            else "",
        ],
        RESOLVE: [
            (
                0,
                2,
                lambda msg, attributes: (
                    COVER_DOMAIN,
                    SERVICE_SET_COVER_POSITION,
                    {ATTR_POSITION: msg[1]},
                )
                if len(msg) > 1
                else (
                    COVER_DOMAIN,
                    SERVICE_OPEN_COVER
                    if msg[0] == MSG_ON
                    else SERVICE_CLOSE_COVER
                    if msg[0] == MSG_OFF
                    else SERVICE_STOP_COVER,
                    None,
                ),
            )
        ],
    },
    FAN_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_FAN,
        GENERATE: [
            lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF,
            lambda state, attributes: min(
                round(attributes[ATTR_PERCENTAGE] / attributes[ATTR_PERCENTAGE_STEP]), 4
            )
            if has_key(attributes, ATTR_PERCENTAGE)
            and has_key(attributes, ATTR_PERCENTAGE_STEP)
            else "",
            lambda state, attributes: 1
            if has_key(attributes, ATTR_OSCILLATING) and attributes[ATTR_OSCILLATING]
            else 0
            if has_key(attributes, ATTR_OSCILLATING)
            else "",
        ],
        RESOLVE: [
            (
                0,
                2,
                lambda msg, attributes: (
                    FAN_DOMAIN,
                    SERVICE_SET_PERCENTAGE,
                    {
                        ATTR_PERCENTAGE: min(
                            max(msg[1], 1) * attributes[ATTR_PERCENTAGE_STEP], 100
                        )
                    },
                )
                if len(msg) > 1 and has_key(attributes, ATTR_PERCENTAGE_STEP)
                else (
                    FAN_DOMAIN,
                    SERVICE_TURN_ON if msg[0] == MSG_ON else SERVICE_TURN_OFF,
                    None,
                ),
            ),
            (
                2,
                3,
                lambda msg, attributes: (
                    FAN_DOMAIN,
                    SERVICE_OSCILLATE,
                    {ATTR_OSCILLATING: msg[0] == 1},
                ),
            ),
        ],
    },
    CLIMATE_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_CLIMATE,
        GENERATE: [
            lambda state, attributes: MSG_OFF if state == HVAC_MODE_OFF else MSG_ON,
            lambda state, attributes: SUPPORTED_HVAC_MODES.index(state) + 1
            if state in SUPPORTED_HVAC_MODES
            else "",
            lambda state, attributes: round(attributes[ATTR_TEMPERATURE])
            if has_key(attributes, ATTR_TEMPERATURE)
            else "",
        ],
        RESOLVE: [
            (
                0,
                2,
                lambda msg, attributes: (
                    CLIMATE_DOMAIN,
                    SERVICE_SET_HVAC_MODE,
                    {ATTR_HVAC_MODE: SUPPORTED_HVAC_MODES[msg[1] - 1]},
                )
                if len(msg) > 1 and msg[1] >= 1 and msg[1] <= 5
                else (CLIMATE_DOMAIN, SERVICE_TURN_ON, None)
                if msg[0] == MSG_ON and len(msg) == 1
                else (CLIMATE_DOMAIN, SERVICE_TURN_OFF, None),
            ),
            (
                2,
                3,
                lambda msg, attributes: (
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {ATTR_TEMPERATURE: msg[0]},
                ),
            ),
        ],
    },
    # following domains fallback to switch
    VACUUM_DOMAIN: {
        SUFFIX: TOPIC_SUFFIX_SWITCH,
        GENERATE: [
            lambda state, attributes: MSG_ON
            if state in [STATE_ON, STATE_CLEANING]
            else MSG_OFF
        ],
        RESOLVE: [
            (
                0,
                1,
                lambda msg, attributes: (
                    VACUUM_DOMAIN,
                    SERVICE_START
                    if msg[0] == MSG_ON
                    and attributes[ATTR_SUPPORTED_FEATURES] & SUPPORT_START
                    else SERVICE_TURN_ON
                    if msg[0] == MSG_ON
                    else SERVICE_RETURN_TO_BASE
                    if msg[0] == MSG_OFF
                    and attributes[ATTR_SUPPORTED_FEATURES] & SUPPORT_RETURN_HOME
                    else SERVICE_STOP
                    if msg[0] == MSG_OFF
                    and attributes[ATTR_SUPPORTED_FEATURES] & SUPPORT_STOP
                    else SERVICE_TURN_OFF,
                    None,
                ),
            )
        ],
    },
    SCRIPT_DOMAIN: gen_switch_config(SCRIPT_DOMAIN),
    AUTOMATION_DOMAIN: gen_switch_config(AUTOMATION_DOMAIN),
    INPUT_BOOLEAN_DOMAIN: gen_switch_config(INPUT_BOOLEAN_DOMAIN),
    SCENE_DOMAIN: gen_switch_config(
        service_domain=SCENE_DOMAIN,
        generate=lambda state, attributes: MSG_OFF,
    ),
    GROUP_DOMAIN: gen_switch_config(
        HOMEASSISTANT_DOMAIN  # note: service domain for GROUP is homeassistant
    ),
    CAMERA_DOMAIN: gen_switch_config(
        service_domain=CAMERA_DOMAIN,
        generate=lambda state, attributes: MSG_OFF if state == STATE_IDLE else MSG_ON,
    ),
    HUMIDIFIER_DOMAIN: gen_switch_config(HUMIDIFIER_DOMAIN),
    MEDIA_PLAYER_DOMAIN: gen_switch_config(
        service_domain=MEDIA_PLAYER_DOMAIN,
        generate=lambda state, attributes: MSG_ON
        if state == STATE_PLAYING
        else MSG_OFF,
    ),
    LOCK_DOMAIN: gen_switch_config(
        service_domain=LOCK_DOMAIN,
        generate=lambda state, attributes: MSG_OFF if state == STATE_LOCKED else MSG_ON,
        service_on=SERVICE_UNLOCK,
        service_off=SERVICE_LOCK,
    ),
    REMOTE_DOMAIN: gen_switch_config(REMOTE_DOMAIN),
}

"""
UNSUPPORTED_DOMAINS = [
    "alarm_control_panel",
    "button",
    "demo",
    "device_tracker",
    "input_button",
    "input_select",
    "person",
    "select",
]
"""
