# controllers/speaker_controller.py

from .alexa_controller import AlexaController

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
    def handle_directive(name, payload):
        # RICHTUNG: ALEXA -> MQTT/DB
        
        if name == "SetVolume":
            # Alexa schickt: {"volume": 30}
            volume = payload.get('volume', 20)
            return {"volume": volume}
            
        elif name == "SetMute":
            # Alexa schickt: {"mute": true}
            mute_state = payload.get('mute', False)
            return {"muted": mute_state}
            
        elif name == "AdjustVolume":
            # Alexa schickt ein Delta: {"volume": -10, "volumeDefault": False}
            # Da wir hier keinen Zugriff auf den DB-Stand haben, geben wir das Delta weiter.
            # Dein MQTT-Handler oder das Device muss dann: current_vol + delta rechnen.
            delta = payload.get('volume', 0)
            return {"volume_delta": delta}
            
        return {}

