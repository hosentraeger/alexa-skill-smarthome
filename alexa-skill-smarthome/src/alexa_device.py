# alexa_device.py

import boto3
import os

DEFAULT_MANUFACTURER_NAME = os.environ.get("MANUFACTURER_NAME", "A.C.M.E. Corp")

from controllers import (
    PowerController, BrightnessController, SpeakerController, 
    TemperatureSensor, RollershutterController, ColorController,
    ColorTemperatureController, MotionSensor, ContactSensor,
    HumiditySensor, ThermostatController, StepSpeakerController,
    SceneController, ToggleController
)

CONTROLLER_MAPPING = {
    "PowerController": PowerController,
    "BrightnessController": BrightnessController,
    "SpeakerController": SpeakerController,
    "TemperatureSensor": TemperatureSensor,
    "RollershutterController": RollershutterController,
    "ColorController": ColorController,
    "ColorTemperatureController": ColorTemperatureController,
    "MotionSensor": MotionSensor,
    "ContactSensor": ContactSensor,
    "HumiditySensor": HumiditySensor,
    "ThermostatController": ThermostatController,
    "StepSpeakerController": StepSpeakerController,
    "SceneController": SceneController,
    "ToggleController": ToggleController
}

class AlexaDevice:
    def __init__(self, record):
        self.endpoint_id = record['device_id']
        self.item_name = record['item_name']
        self.friendly_name = record.get('friendly_name', self.item_name)
        self.description = record.get('description', self.item_name)
        self.manufacturer_name = record.get('manufacturer_name', DEFAULT_MANUFACTURER_NAME)

        # Neue Attribute für additionalAttributes
        self.firmware_version = record.get('firmware_version', 'v1.0')
        self.software_version = record.get('software_version', 'v1.0')
        self.model_name = record.get('model_name', 'top model')
        self.serial_number = record.get('serial_number', self.endpoint_id[:8]) # Beispiel
        
        # Kategorien (Alexa erwartet eine Liste)
        cat = record.get('device_category', 'OTHER')
        self.display_categories = [cat] if isinstance(cat, str) else cat
        
        self.proactive = record.get('proactivelyReported', False)
        self.retrievable = record.get('retrievable', True)
        self.handle_generic = record.get('OpenHABHandleGeneric', True)
        self.enabled = record.get('enabled', True)
        
        # Den State als Member speichern
        self.raw_state = record.get('state', {})

        # Controller initialisieren
        self.controllers = []
        for cap_name in record.get('capabilities', []):
            controller_class = CONTROLLER_MAPPING.get(cap_name)
            if controller_class:
                self.controllers.append(controller_class)

    def get_discovery_capabilities(self):
        """Erstellt die Liste aller Capabilities für die Discovery."""
        # Jedes Smart Home Gerät braucht das Basis-Interface
        caps = []
        
        # Alle dynamischen Controller (Power, Brightness, etc.)
        for ctrl in self.controllers:
            caps.append(ctrl.get_capability(self.proactive, self.retrievable))
            
        # Jedes Gerät braucht EndpointHealth
        caps.append({
            "type": "AlexaInterface",
            "interface": "Alexa.EndpointHealth",
            "version": "3",
            "properties": {
                "supported": [{"name": "connectivity"}],
                "retrievable": True,
                "proactivelyReported": True
            }
        })

        # 3. Das Basis Alexa Interface (immer am Schluss)
        caps.append({
            "type": "AlexaInterface",
            "interface": "Alexa",
            "version": "3"
        })

        return caps


    def get_all_properties(self):
        """Nutzt jetzt die internen Daten der Klasse."""
        all_props = []
        
        # Normalisierung
        if isinstance(self.raw_state, dict):
            full_state = self.raw_state
        else:
            full_state = {
                "power": self.raw_state,
                "brightness": self.raw_state,
                "temperature": self.raw_state,
                "value": self.raw_state,
                "color": self.raw_state,
                "colorTemperatureInKelvin": self.raw_state
            }

        for controller in self.controllers:
            # Zugriff auf die statische Methode der Controller-Klasse
            props = controller.get_properties(full_state)
            all_props.extend(props)
            
        return all_props
        
    def get_discovery_payload(self):
        """Erzeugt das vollständige Objekt für einen Endpunkt im Discovery-Payload."""
        
        # 1. Capabilities sammeln (Nutzt deine Logik aus get_discovery_capabilities)
        # Wir können get_discovery_capabilities() hier direkt aufrufen
        capabilities = self.get_discovery_capabilities()

        # 2. Das vollständige Endpunkt-Objekt zurückgeben
        return {
            "endpointId": self.endpoint_id,
            "friendlyName": self.friendly_name,
            "description": self.description,
            "manufacturerName": self.manufacturer_name,
            "displayCategories": self.display_categories,
            "additionalAttributes": {
                "firmwareVersion": self.firmware_version,
                "manufacturer": self.manufacturer_name,
                "model": self.model_name,
                "serialNumber": self.serial_number,
                "customIdentifier": f"redfive-{self.endpoint_id[-4:]}",
                "softwareVersion": self.software_version
            },
            "capabilities": capabilities,
            "cookie": {}
        }

    def execute_directive(self, directive):
        header = directive.get('header', {})
        payload = directive.get('payload', {})
        namespace = header.get('namespace')
        name = header.get('name')

        target_controller = next((c for c in self.controllers if c.namespace == namespace), None)

        if target_controller:
            # Der Controller liefert jetzt beide Welten zurück
            result = target_controller.handle_directive(name, payload, current_state=self.raw_state)

            if result:
                # 1. Speichern im Alexa-Format (DynamoDB)
                alexa_data = result.get("alexa")
                if alexa_data:
                    self.raw_state.update(alexa_data)
                    self.update_db()

                # 2. Rückgabe des OpenHAB-Formats für den Lambda-Handler
                return result.get("openhab")

        return None


    def update_db(self):
        """Schreibt den aktuellen raw_state zurück in die DynamoDB."""

        # Nutze die Umgebungsvariable oder einen Standardnamen
        table_name = os.environ.get('DDB_TABLE', 'smarthome_devices')
        region = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1') # Deine Region!

        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)

        print(f"[DB] Aktualisiere Status für {self.endpoint_id}...")
        
        try:
            table.update_item(
                Key={'device_id': self.endpoint_id},
                UpdateExpression="set #s = :s",
                ExpressionAttributeNames={'#s': 'state'},
                ExpressionAttributeValues={':s': self.raw_state}
            )
            return True
        except Exception as e:
            print(f"[DB] Fehler beim Update: {e}")
            return False