# controllers/__init__.py

from .power_controller import PowerController
from .brightness_controller import BrightnessController
from .speaker_controller import SpeakerController
from .temperature_sensor import TemperatureSensor
from .rollershutter_controller import RollershutterController
from .color_controller import ColorController
from .color_temperature_controller  import ColorTemperatureController
from .contact_sensor import ContactSensor
from .humidity_sensor import HumiditySensor
from .motion_sensor import MotionSensor
from .scene_controller import SceneController
from .step_speaker_controller import StepSpeakerController
from .thermostat_controller import ThermostatController
from .toggle_controller import ToggleController

# Optional: Eine Liste aller verfügbaren Controller für dynamische Checks
__all__ = [
    'PowerController',
    'BrightnessController',
    'SpeakerController',
    'TemperatureSensor',
    'RollershutterController',
    "ColorController",
    "ColorTemperatureController",
    "ContactSensor",
    "HumiditySensor",
    "MotionSensor",
    "SceneController",
    "StepSpeakerController",
    "ThermostatController",
    "ToggleController"
]