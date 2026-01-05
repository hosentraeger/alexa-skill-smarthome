# controllers/motion_sensor.py

from .alexa_controller import AlexaController
import logging

logger = logging.getLogger(__name__)


class MotionSensor(AlexaController):
    namespace = "Alexa.MotionSensor"

    @staticmethod
    def get_capability(proactive=True, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.MotionSensor",
            "version": "3",
            "properties": {
                "supported": [{"name": "detectionState"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Wir erwarten 'DETECTED' oder 'NOT_DETECTED'
        # Default auf 'NOT_DETECTED', um Fehlalarme zu vermeiden
        value = state_dict.get('detectionState', 'NOT_DETECTED')

        # Validierung des Formats
        if value not in ("DETECTED", "NOT_DETECTED"):
            logger.warning(f"MotionSensor: Ungültiger Status '{value}'. Nutze NOT_DETECTED.")
            value = "NOT_DETECTED"

        return [{
            "namespace": "Alexa.MotionSensor",
            "name": "detectionState",
            "value": value  # Direkter String, kein Dict!
        }]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        # MotionSensoren empfangen normalerweise keine Direktiven von Alexa,
        # aber das Interface muss für den Discovery/Handler-Loop existieren.
        return {}

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if state in ["ON", "OFF"]:
            # ON -> Bewegung, OFF -> Keine Bewegung
            val = "DETECTED" if state == "ON" else "NOT_DETECTED"
            return {"detectionState": val}
        return {}
