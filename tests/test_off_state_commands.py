"""Exercise production parsing methods without requiring a running HA."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).parents[1] / "custom_components/bemfa"


def load_method(filename, class_name, method_name, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)
    method.returns = None
    for arg in method.args.args:
        arg.annotation = None
    module = ast.Module(body=[method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), filename, "exec"), namespace)
    return namespace[method_name]


class FakeFan:
    pass


NS = {
    "MSG_OFF": "off", "MSG_ON": "on", "MSG_SEPARATOR": "#",
    "STATE_ON": "on", "ATTR_ENTITY_ID": "entity_id", "DOMAIN": "fan",
    "ATTR_PERCENTAGE": "percentage", "ATTR_PERCENTAGE_STEP": "percentage_step",
    "ATTR_OSCILLATING": "oscillating", "SERVICE_SET_PERCENTAGE": "set_percentage",
    "SERVICE_TURN_ON": "turn_on", "SERVICE_TURN_OFF": "turn_off",
    "SERVICE_OSCILLATE": "oscillate", "has_key": lambda attrs, key: key in attrs,
}
FakeFan.resolve_msg = load_method("sync.py", "ControllableSync", "resolve_msg", NS)
FakeFan._generate_msg_parts = load_method("sync.py", "ControllableSync", "_generate_msg_parts", NS)
FakeFan._msg_resolvers = load_method("sync_fan.py", "Fan", "_msg_resolvers", NS)
FakeFan._msg_generators = load_method("sync_fan.py", "Fan", "_msg_generators", NS)


class TestOffStateCommands(unittest.TestCase):
    def fan(self, state="off", percentage=0):
        fan = FakeFan()
        fan._entity_id = "fan.test"
        fan._hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda _: SimpleNamespace(
                state=state, attributes={"percentage": percentage, "percentage_step": 25})),
            services=SimpleNamespace(call=Mock()),
        )
        return fan

    def test_all_four_levels_from_off(self):
        for level in range(1, 5):
            with self.subTest(level=level):
                fan = self.fan()
                fan.resolve_msg(f"on#{level}")
                fan._hass.services.call.assert_called_once_with(
                    domain="fan", service="set_percentage",
                    service_data={"percentage": level * 25, "entity_id": "fan.test"})

    def test_plain_on_remains_turn_on(self):
        fan = self.fan()
        fan.resolve_msg("on")
        fan._hass.services.call.assert_called_once_with(
            domain="fan", service="turn_on", service_data={"entity_id": "fan.test"})

    def test_repeated_command_is_not_echoed(self):
        fan = self.fan("on", 25)
        fan.resolve_msg("on#1")
        fan._hass.services.call.assert_not_called()

    def test_off_discards_arguments(self):
        fan = self.fan("on", 100)
        fan.resolve_msg("off#4#1")
        fan._hass.services.call.assert_called_once_with(
            domain="fan", service="turn_off", service_data={"entity_id": "fan.test"})

    def test_change_level_while_on(self):
        fan = self.fan("on", 100)
        fan.resolve_msg("on#3")
        fan._hass.services.call.assert_called_once_with(
            domain="fan", service="set_percentage",
            service_data={"percentage": 75, "entity_id": "fan.test"})


if __name__ == "__main__":
    unittest.main()
