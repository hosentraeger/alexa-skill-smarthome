# controllers/alexa_controller.py

from abc import ABC, abstractmethod

class AlexaController(ABC):
    @property
    @abstractmethod
    def namespace(self):
        pass

    @staticmethod
    @abstractmethod
    def get_capability(proactive=False, retrievable=True):
        """Gibt das Discovery-JSON zurück."""
        pass

    @staticmethod
    @abstractmethod
    def get_properties(state_value):
        """Gibt die Liste der Properties für StateReports zurück."""
        pass

    @staticmethod
    def handle_directive(name, payload):
        """Verarbeitet eine Direktive"""
        return {}

    @staticmethod
    def handle_update(update_dict):
        """Übersetzt Hardware-Status (z.B. von OpenHAB) -> Datenbank-Status."""
        return {}