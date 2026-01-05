# controllers/thermostat_controller.py

import logging
from .alexa_controller import AlexaController

logger = logging.getLogger(__name__)


class ThermostatController(AlexaController):
    namespace = "Alexa.ThermostatController"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.ThermostatController",
            "version": "3",
            "properties": {
                "supported": [
                    {"name": "targetSetpoint"},
                    {"name": "thermostatMode"}
                ],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            },
            "configuration": {
                "supportedModes": ["HEAT", "COOL", "AUTO", "OFF"]
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Fallbacks
        target_temp = state_dict.get('targetSetpoint', 21.0)
        mode = state_dict.get('thermostatMode', 'HEAT')

        # Sicherstellen, dass die Werte Floats/Strings sind
        try:
            target_value = float(target_temp)
        except (ValueError, TypeError):
            target_value = 21.0

        return [
            {
                "namespace": "Alexa.ThermostatController",
                "name": "targetSetpoint",
                "value": {
                    "value": target_value,
                    "scale": "CELSIUS"
                }
            },
            {
                "namespace": "Alexa.ThermostatController",
                "name": "thermostatMode",
                "value": mode
            }
        ]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"ThermostatController: Handling '{name}'")

        alexa_state = {}
        oh_command = None

        # 1. Zieltemperatur direkt setzen
        if name == "SetTargetSetpoint":
            temp = payload.get('targetSetpoint', {}).get('value')
            if temp is not None:
                alexa_state = {"targetSetpoint": float(temp)}
                oh_command = float(temp)

        # 2. Temperatur relativ anpassen ("Alexa, stell die Heizung 2 Grad höher")
        elif name == "AdjustTargetSetpoint":
            current_temp = current_state.get('targetSetpoint', 21.0) if current_state else 21.0
            delta = payload.get('targetSetpointDelta', {}).get('value', 0)
            new_temp = round(current_temp + delta, 1)

            alexa_state = {"targetSetpoint": new_temp}
            oh_command = new_temp

        # 3. Modus ändern (HEAT, COOL, AUTO, OFF)
        elif name == "SetThermostatMode":
            mode = payload.get('thermostatMode', {}).get('value')
            if mode:
                alexa_state = {"thermostatMode": mode}
                oh_command = mode

        if alexa_state:
            return {
                "alexa": alexa_state,
                "openhab": oh_command
            }

        return {}

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if state is None:
            return {}

        # 1. Fall: Modus-Update (HEAT, COOL, AUTO, OFF)
        # Wenn OpenHAB einen der unterstützten Modi sendet
        supported_modes = ["HEAT", "COOL", "AUTO", "OFF"]
        if str(state).upper() in supported_modes:
            return {"thermostatMode": str(state).upper()}

        # 2. Fall: Zieltemperatur-Update (Zahl)
        # Wenn der Wert eine Zahl ist (und kein Modus), gehen wir vom Setpoint aus
        try:
            temp_value = float(state)
            # Ein Plausibilitätscheck (z.B. Setpoints liegen meist zwischen 4 und 35 Grad)
            if 4.0 <= temp_value <= 35.0:
                return {"targetSetpoint": temp_value}
        except (ValueError, TypeError):
            pass

        return {}
