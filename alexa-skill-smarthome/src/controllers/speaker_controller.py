# controllers/speaker_controller.py

import logging
from .alexa_controller import AlexaController

logger = logging.getLogger(__name__)

class SpeakerController(AlexaController):
    namespace = "Alexa.Speaker"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface", "interface": "Alexa.Speaker", "version": "3",
            "properties": {
                "supported": [{"name": "volume"}, {"name": "muted"}],
                "retrievable": retrievable, "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Holt sich gezielt seine zwei Werte aus dem DB-Dictionary
        return [
            {
                "namespace": "Alexa.Speaker",
                "name": "volume",
                "value": state_dict.get('volume', 0)
            },
            {
                "namespace": "Alexa.Speaker",
                "name": "muted",
                "value": state_dict.get('muted', False)
            }
        ]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"SpeakerController: Handling '{name}'")

        new_volume = None

        # 1. Absolute Lautstärke: "Stelle Lautstärke auf 30"
        if name == "SetVolume":
            new_volume = int(payload.get('volume', 0))

        # 2. Relative Lautstärke: "Mach lauter / leiser"
        elif name == "AdjustVolume":
            # Wir holen den aktuellen Wert (Standard 10, falls leer)
            current_val = current_state.get('volume', 10) if current_state else 10

            # volumeDelta ist positiv (lauter) oder negativ (leiser)
            delta = payload.get('volume', 0)

            # Berechnung mit Grenzen 0 bis 100
            new_volume = max(0, min(100, int(current_val + delta)))
            logger.info(f"Volume adjustment: {current_val} -> {new_volume} (Delta: {delta})")

        # 3. Stummschalten: "Stumm" / "Ton an"
        elif name == "SetMute":
            mute_state = payload.get('mute', False)
            return {
                "alexa": {"muted": mute_state},
                "openhab": "ON" if mute_state else "OFF"
            }

        if new_volume is not None:
            return {
                "alexa": {"volume": new_volume},
                "openhab": new_volume
            }

        logger.warning(f"SpeakerController: Directive '{name}' not supported.")
        return {}

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")

        # 1. Check auf Stummschaltung (ON/OFF)
        if state in ["ON", "OFF"]:
            return {"muted": True if state == "ON" else False}

        # 2. Check auf Lautstärke (Zahl)
        try:
            # Wenn es eine Zahl ist, mappen wir sie auf 'volume'
            vol = int(float(state))
            if 0 <= vol <= 100:
                return {"volume": vol}
        except (ValueError, TypeError):
            pass

        return {}
