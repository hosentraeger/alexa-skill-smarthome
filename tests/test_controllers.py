import sys
import os

# WICHTIG: Pfad zum src-Ordner hinzufügen, damit die Imports gefunden werden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controllers.humidity_sensor import HumiditySensor
from controllers.power_controller import PowerController

def test_humidity_logic():
    # Testet das Mapping von OpenHAB-String zu Alexa-Float
    update = {"state": "65.5"}
    result = HumiditySensor.handle_update(update)
    assert result["relativeHumidity"] == 65.5

def test_power_logic():
    # Testet das Power-Mapping
    update = {"state": "ON"}
    result = PowerController.handle_update(update)
    assert result["powerState"] == "ON"