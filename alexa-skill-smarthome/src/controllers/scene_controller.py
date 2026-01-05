# controllers/scene_controller.py

import logging
from .alexa_controller import AlexaController

logger = logging.getLogger(__name__)


class SceneController(AlexaController):
    namespace = "Alexa.SceneController"

    @staticmethod
    def get_capability(proactive=False, retrievable=False):
        # Szenen sind meistens nicht abfragbar (retrievable=False),
        # da sie einen Aktions-Trigger darstellen, keinen dauerhaften Zustand.
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.SceneController",
            "version": "3",
            "supportsDeactivation": False,  # Auf True setzen, wenn die Szene auch "aus" geschaltet werden kann
            "proactivelyReported": proactive
        }

    @staticmethod
    def get_properties(state_dict):
        # Szenen haben in der Regel keine abfragbaren Properties im Sinne von ReportState.
        # Wenn eine Szene aktiviert wurde, wird dies über ein Event (Alexa.SceneController.ActivationStarted) gemeldet.
        return []

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"SceneController: Handling directive '{name}' with payload: {payload}")

        if name not in ("Activate", "Deactivate"):
            logger.warning(f"SceneController: Directive '{name}' not supported.")
            return {}

        oh_state = "OFF"
        alexa_state = {"scene_status": "DEACTIVATED"}

        if name == "Activate":
            # Wenn der Nutzer sagt: "Alexa, aktiviere [Szenenname]"
            # Wir geben einen Status zurück, der an die Hardware (MQTT/OpenHAB) geht.
            # 'last_activated' dient hier nur als DB-Eintrag zur Info.
            import datetime
            now = datetime.datetime.now().isoformat()
            oh_state = "ON"
            alexa_state = {"scene_status": "ACTIVATED","last_activated": now }
            logger.info("SceneController: Scene activation triggered.")
        else:
            # Nur relevant, wenn supportsDeactivation oben auf True steht.
            logger.info("SceneController: Scene deactivation triggered.")

        return {
            "alexa": alexa_state,
            "openhab": oh_state
        }

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if not state:
            return {}

        # Wenn die Szene in OpenHAB aktiviert wurde (meistens Status "ON")
        if state == "ON":
            import datetime
            # Wir nutzen UTC, damit Alexa den Zeitstempel versteht
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            return {
                "scene_status": "ACTIVATED",
                "last_activated": now
            }

        # Optional: Wenn die Szene deaktiviert wurde
        elif state == "OFF":
            return {"scene_status": "DEACTIVATED"}

        return {}