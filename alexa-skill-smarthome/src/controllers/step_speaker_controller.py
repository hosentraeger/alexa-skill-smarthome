# controllers/step_speaker_controller.py

import logging
from .alexa_controller import AlexaController

logger = logging.getLogger(__name__)


class StepSpeakerController(AlexaController):
    namespace = "Alexa.StepSpeakerController"

    @staticmethod
    def get_capability(proactive=False, retrievable=False):
        # StepSpeaker hat normalerweise keine abfragbaren Eigenschaften (retrievable=False),
        # da es nur relative Befehle (lauter/leiser) sendet.
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.StepSpeakerController",
            "version": "3",
            "properties": {
                "supported": []  # Dieses Interface hat keine abfragbaren Properties
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Da es keine abfragbaren Properties gibt, geben wir eine leere Liste zurück.
        return []

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        if name == "AdjustVolume":
            # Hier gibt es kein 'alexa' Resultat für die DB,
            # da wir den absoluten Wert nicht kennen.
            # Wir schicken nur den Befehl an OpenHAB.
            steps = payload.get('volumeSteps', 1)

            # Wenn steps positiv ist -> lauter, negativ -> leiser
            oh_command = "UP" if steps > 0 else "DOWN"

            return {
                "openhab": oh_command
            }
        return {}

    @staticmethod
    def handle_update(update_dict):
        """
        StepSpeaker haben keinen absoluten Zustand (volume/muted).
        Daher liefern wir hier immer ein leeres Dict zurück.
        """
        # Selbst wenn OpenHAB ein Update schickt, kann Alexa
        # mit diesem Interface keine Status-Änderungen verarbeiten.
        return {}