# lambda_function.py
import logging
import json
import time
from alexa_auth import handle_accept_grant
from alexa_device import AlexaDevice

import boto3
import os

from alexa_device import AlexaDevice
from alexa_response import AlexaResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DEPLOY_DATE = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

# alexa_discovery.py
from alexa_device import AlexaDevice
from alexa_response import AlexaResponse

# Boto3 Ressourcen außerhalb des Handlers initialisieren
# (Dadurch werden sie bei Warm-Starts wiederverwendet)
db_resource = boto3.resource("dynamodb")

# Den Tabellennamen aus einer Umgebungsvariable lesen (Best Practice)
# Falls nicht gesetzt, nutzen wir den Fallback-Namen
DDB_TABLE_NAME = os.environ.get("DDB_TABLE", "smarthome_devices")

# Die Table-Referenz erstellen
table = db_resource.Table(DDB_TABLE_NAME)

# IoT Client für MQTT (außerhalb der Funktion für Re-use)
iot_client = boto3.client("iot-data")

def handle_discovery(devices_records):
    """
    Erstellt die Antwort auf den Alexa.Discovery / Discover Request.
    Nutzt die Logik der AlexaDevice-Klasse.
    """
    # Initialisiere die Antwort-Struktur
    adr = AlexaResponse(name="Discover.Response", namespace="Alexa.Discovery")
    
    endpoints = []
    for record in devices_records:
        # 1. Filter: Nur enabled Geräte
        # Hier nutzen wir den record direkt, um gar nicht erst das Objekt zu bauen
        if not record.get('enabled', True):
            continue

        # 2. AlexaDevice Objekt erstellen
        # Das Objekt weiß selbst, wie es seine Capabilities und Payloads baut
        device = AlexaDevice(record)
        
        # 3. Das fertige Endpunkt-Dict von der Klasse abholen
        # get_discovery_payload() liefert genau das Format, das Alexa erwartet
        endpoints.append(device.get_discovery_payload())

    # 4. Die Liste der Endpunkte in die Response setzen und das finale JSON liefern
    adr.set_payload_endpoints(endpoints)
    return adr.get()

def handle_control(device, request):
    """
    Verarbeitet alle Steuerungsbefehle (TurnOn, SetBrightness, SetMode, etc.)
    """
    directive = request["directive"]
    header = directive["header"]
    endpoint_id = directive["endpoint"]["endpointId"]
    correlation_token = header.get("correlationToken")
    token = directive["endpoint"]["scope"]["token"]
    # Sicherer Zugriff auf das Token (analog zu handle_report_state)
    scope = directive["endpoint"].get("scope", {})
    token = scope.get("token", "no-token")

    namespace = header.get("namespace")
    name = header.get("name")
    payload = directive.get("payload", {})
    
    # Befehl ausführen (Die Magie der Controller nutzen)
    mqtt_data = device.execute_directive(directive)

    if mqtt_data:
      handle_generic = getattr(device, 'handle_generic', True) 
      item_name = getattr(device, 'item_name', device.endpoint_id)
      alexa_message = {
            "endpointId": endpoint_id,
            "openHABItemName": item_name,
            "openHABHandleGeneric": handle_generic,
            "nameSpace": namespace,
            "requestMethod": name,
            "payload": mqtt_data
        }
      logger.info("mqtt alexa message: %s\n", json.dumps(alexa_message))
      # Hardware informieren via MQTT
      iot_client.publish(
          topic="alexa",
          qos=1,
          payload=json.dumps(alexa_message)
      )
        
      # Neuen Status permanent in DB speichern
      device.update_db()
    else:
      logger.error("no mqtt payload!")
    # Erfolgs-Antwort für Alexa bauen
    adr = AlexaResponse(
        name="Response",
        namespace="Alexa",
        correlation_token=correlation_token,
        endpoint_id=endpoint_id,
        token=token
    )

    # Alle aktuellen Properties (inkl. der Änderung) in den Context packen
    for prop in device.get_all_properties():
        adr.add_context_property(**prop)

    return adr.get()

def handle_report_state(device, request):
    """
    Antwortet auf Alexa.ReportState Anfragen.
    """
    header = request["directive"]["header"]
    correlation_token = header.get("correlationToken")
    
    # Sicherer Zugriff auf das Token
    endpoint = request["directive"].get("endpoint", {})
    scope = endpoint.get("scope", {})
    token = scope.get("token", "no-token-provided") # Fallback für Tests

    endpoint_id = device.endpoint_id

    adr = AlexaResponse(
        name="StateReport",
        namespace="Alexa",
        correlation_token=correlation_token,
        endpoint_id=endpoint_id,
        token=token
    )

    for prop in device.get_all_properties():
        adr.add_context_property(**prop)

    return adr.get()
    

def lambda_handler(request, context):
    logger.info(f"--- LAMBDA START: {DEPLOY_DATE} ---")

    # Logge den kompletten Request, damit wir sehen, was Alexa genau will
    logger.info("FULL REQUEST: %s", json.dumps(request))
    
    if "directive" not in request:
        return {}

    header = request["directive"]["header"]
    namespace = header["namespace"]
    name = header["name"]

    logger.info(f"Namespace: {namespace} | Name: {name}")

    # 1. AUTHENTIFIZIERUNG (AcceptGrant)
    if namespace == "Alexa.Authorization" and name == "AcceptGrant":
        return handle_accept_grant(request)

    # 2. DISCOVERY
    if namespace == "Alexa.Discovery" and name == "Discover":
        # Alle aktiven Geräte aus der DynamoDB laden
        response = table.scan() # Oder ein Filter auf 'active'
        records = response.get('Items', [])
        
        response = handle_discovery(records)
        logger.info("DISCOVERY RESPONSE: %s", json.dumps(response))
        
        return response

    # 3. STATUS & CONTROL
    # Hier laden wir das Device und entscheiden zwischen ReportState und Control
    endpoint_id = request["directive"]["endpoint"]["endpointId"]

    # Device-Daten aus DynamoDB holen
    res = table.get_item(Key={'device_id': endpoint_id})
    record = res.get('Item')
    if not record:
        logger.error(f"Device {endpoint_id} nicht in Datenbank gefunden!")
        # Hier könnte man eine Error-Response schicken, 
        # aber wir definieren jetzt das device-Objekt:
        return {} 

    # Jetzt erstellen wir das device-Objekt
    device = AlexaDevice(record)
    
    if name == "ReportState":
        response = handle_report_state(device, request)
        logger.info("CONTROL RESPONSE: %s", json.dumps(response))
        return response

    # Standard: Control Directives (TurnOn, SetPercentage, etc.)

    response = handle_control(device, request)
    logger.info("CONTROL RESPONSE: %s", json.dumps(response))
    return response
