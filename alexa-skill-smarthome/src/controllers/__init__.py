# controllers/__init__.py

from .power_controller import PowerController
from .brightness_controller import BrightnessController
from .speaker_controller import SpeakerController
from .temperature_sensor import TemperatureSensor
from .rollershutter_controller import RollershutterController

# Optional: Eine Liste aller verfügbaren Controller für dynamische Checks
__all__ = [
    'PowerController',
    'BrightnessController',
    'SpeakerController',
    'TemperatureSensor',
    'RollershutterController'
]