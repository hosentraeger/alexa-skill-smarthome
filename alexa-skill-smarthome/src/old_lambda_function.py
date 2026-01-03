# -*- coding: utf-8 -*-

import boto3
from boto3.dynamodb.conditions import Key
import json
import logging
from alexa.skills.smarthome import AlexaResponse
import os
import time
import urllib.request
import urllib.parse
import uuid
from datetime import datetime, timezone

# --- INITIALISIERUNG ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

aws_dynamodb = boto3.client("dynamodb")
db_resource = boto3.resource("dynamodb")
iot_client = boto3.client("iot-data")
ssm = boto3.client("ssm")

DDB_TABLE = "smarthome_devices"
table = db_resource.Table(DDB_TABLE)
MANUFACTURER_NAME = "redfive"

CLIENT_ID = os.environ.get("ALEXA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ALEXA_CLIENT_SECRET")

DEPLOY_DATE = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

# --- HAUPTHANDLER ---

def lambda_handler(request, context):
    # 1. Weiche: Interner Batch-Trigger (Discovery Initialisierung oder MQTT)
    if request.get("action") == "internal_proactive_batch":
        return handle_proactive_batch(request)

    # 2. Weiche: MQTT Trigger (direkt von IoT Core Rule)
    if "device_name" in request and "state" in request:
        return handle_mqtt_update(request)

    # 3. Weiche: Standard Alexa Skill Request
    logger.info(f"--- LAMBDA START: {DEPLOY_DATE} ---")
    logger.info("REQUEST: %s", json.dumps(request))

    if "directive" not in request:
        return {}

    header = request["directive"]["header"]
    namespace = header["namespace"]
    name = header["name"]

    if namespace == "Alexa.Authorization" and name == "AcceptGrant":
        return handle_authorization(request)

    if namespace == "Alexa.Discovery" and name == "Discover":
        return handle_discovery()

    if name == "ReportState":
        return handle_report_state(request)

    return handle_control(request)

# --- HILFSFUNKTIONEN FÜR MAPPING ---

def get_proactive_properties(caps, state):
    """Zentrale Logik: Übersetzt DB-Status in Alexa-Properties."""
    props = []
    s_state = str(state)

    if "TemperatureSensor" in caps:
        props.append({
            "namespace": "Alexa.TemperatureSensor",
            "name": "temperature",
            "value": {"value": float(s_state), "scale": "CELSIUS"}
        })
    elif "PowerController" in caps:
        is_on = s_state.upper() in ["ON", "1", "TRUE", "OPENED"]
        props.append({
            "namespace": "Alexa.PowerController",
            "name": "powerState",
            "value": "ON" if is_on else "OFF"
        })
    elif "RangeController" in caps:
        props.append({
            "namespace": "Alexa.RangeController",
            "instance": "Blind.Lift",
            "name": "rangeValue",
            "value": int(float(s_state))
        })
    elif "ModeController" in caps:
        props.append({
            "namespace": "Alexa.ModeController",
            "instance": "Blind.Position",
            "name": "mode",
            "value": s_state if "Position." in s_state else f"Position.{s_state.capitalize()}"
        })

    props.append({
        "namespace": "Alexa.EndpointHealth",
        "name": "connectivity",
        "value": {"value": "OK"}
    })
    return props

# --- AUTHORISIERUNG & TOKENS ---

def handle_authorization(request):
    payload = request.get("directive", {}).get("payload", {})
    grant_code = payload.get("grant", {}).get("code")
    if not grant_code: return {"error": "no_grant_code"}

    url = "https://api.amazon.com/auth/o2/token"
    params = {
        "grant_type": "authorization_code",
        "code": grant_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8")

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            refresh_token = res_body.get("refresh_token")
            if refresh_token:
                ssm.put_parameter(Name="/alexa/refresh_token", Value=refresh_token, Type="SecureString", Overwrite=True)
                logger.info("ERFOLG: Refresh Token gespeichert.")
    except Exception as e:
        logger.error(f"Auth Fehler: {str(e)}")

    return {"event": {"header": {"namespace": "Alexa.Authorization", "name": "AcceptGrant.Response", "messageId": str(uuid.uuid4()), "payloadVersion": "3"}, "payload": {}}}

def get_valid_access_token():
    try:
        res = ssm.get_parameter(Name="/alexa/access_token", WithDecryption=True)
        return res["Parameter"]["Value"]
    except:
        return refresh_alexa_token()

def refresh_alexa_token():
    refresh_token = ssm.get_parameter(Name="/alexa/refresh_token", WithDecryption=True)["Parameter"]["Value"]
    url = "https://api.amazon.com/auth/o2/token"
    params = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode("utf-8"))
        new_at = res["access_token"]
        ssm.put_parameter(Name="/alexa/access_token", Value=new_at, Type="SecureString", Overwrite=True)
        return new_at

def handle_proactive_batch(event):
    import uuid
    from datetime import datetime, timezone
    import time

    device_list = event.get("devices", [])
    wait_time = event.get("wait_period", 0)

    if wait_time > 0:
        logger.info(f"Warte {wait_time}s vor dem Senden...")
        time.sleep(wait_time)

    # Initiales Token aus SSM holen
    access_token = get_valid_access_token()
    logger.info(f"access token: {access_token}")
    url = "https://api.eu.amazonalexa.com/v3/events"

    for device in device_list:
        endpoint_id = device["endpointId"]
        # Das erste Property für den ChangeReport extrahieren
        main_prop = device["properties"][0]

        # Die interne Versand-Funktion (ermöglicht sauberen Retry bei 401)
        def attempt_send(token_to_use):
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Das Payload-Dictionary: Name ist jetzt überall konsistent
            proactive_payload = {
                "context": {
                    "properties": [
                        {
                            "namespace": "Alexa.EndpointHealth",
                            "name": "connectivity",
                            "value": {"value": "OK"},
                            "timeOfSample": now,
                            "uncertaintyInMilliseconds": 0
                        }
                    ]
                },
                "event": {
                    "header": {
                        "namespace": "Alexa",
                        "name": "ChangeReport",
                        "messageId": str(uuid.uuid4()),
                        "payloadVersion": "3"
                    },
                    "endpoint": {
                        "scope": {"type": "BearerToken", "token": token_to_use},
                        "endpointId": endpoint_id
                    },
                    "payload": {
                        "change": {
                            "cause": {"type": "PERIODIC_POLL"},
                            "properties": [
                                {
                                    "namespace": main_prop["namespace"],
                                    "name": main_prop["name"],
                                    "value": main_prop["value"],
                                    "timeOfSample": now,
                                    "uncertaintyInMilliseconds": 0
                                }
                            ]
                        }
                    }
                }
            }
            logger.info("ChangeReport Request: %s\n", json.dumps(proactive_payload).encode('utf-8'))

            # Der eigentliche HTTP Request
            req = urllib.request.Request(
                url, 
                data=json.dumps(proactive_payload).encode('utf-8'), 
                method='POST'
            )
            req.add_header("Authorization", f"Bearer {token_to_use}")
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req) as response:
                return response.getcode()

        # Ausführung mit Fehlerbehandlung und automatischem Token-Refresh
        try:
            status = attempt_send(access_token)
            logger.info(f"Report {endpoint_id}: Status {status}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.info("Token abgelaufen (401). Refreshe und versuche es erneut...")
                # Token im SSM erneuern und für den nächsten Versuch speichern
                access_token = refresh_alexa_token() 
                logger.info(f"new access token: {access_token}")
                try:
                    status = attempt_send(access_token)
                    logger.info(f"Erfolg nach Refresh {endpoint_id}: Status {status}")
                except Exception as retry_e:
                    logger.error(f"Fehler auch nach Refresh für {endpoint_id}: {retry_e}")
            else:
                logger.error(f"HTTP Fehler {e.code} für {endpoint_id}: {e.read().decode('utf-8')}")
        except Exception as e:
            logger.error(f"Unerwarteter Fehler für {endpoint_id}: {str(e)}")

    return {"status": "processed"}



def handle_mqtt_update(event):
    try:
        dev_name = event.get("device_name")
        new_state = event.get("state")
        res = table.query(IndexName="device_name-index", KeyConditionExpression=Key("device_name").eq(dev_name))
        items = res.get("Items", [])
        if not items: return
        
        real_id = items[0]["device_id"]
        raw_caps = items[0].get("capabilities", [])
        caps = [c for c in raw_caps] if isinstance(raw_caps, list) else []

        table.update_item(Key={"device_id": real_id}, UpdateExpression="SET #s = :val", ExpressionAttributeNames={"#s": "state"}, ExpressionAttributeValues={":val": str(new_state)})
        
        device_props = get_proactive_properties(caps, new_state)
        handle_proactive_batch({"action": "internal_proactive_batch", "wait_period": 0, "devices": [{"endpointId": real_id, "properties": device_props}]})
    except Exception as e:
        logger.error(f"MQTT Error: {e}")

def build_capability(adr, cap, proactive, retrievable):
    # Standard-Reporting Flags
    # Wichtig: Für Sensoren erzwingen wir retrievable=True
    is_sensor = cap in ["TemperatureSensor", "EndpointHealth"]
    prop_config = {
        "proactively_reported": proactive,
        "retrievable": True if is_sensor else retrievable,
    }

    # 1. Spezialfall: ModeController (Deine Rolladen-Positionen)
    if cap == "ModeController":
        return [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.ModeController",
                "instance": "Blind.Position",
                "version": "3",
                "properties": {
                    "supported": [{"name": "mode"}],
                    "retrievable": retrievable,
                    "proactivelyReported": proactive,
                },
                "capabilityResources": {
                    "friendlyNames": [
                        {
                            "@type": "asset",
                            "value": {"assetId": "Alexa.Setting.Opening"},
                        }
                    ]
                },
                "configuration": {
                    "ordered": False,
                    "supportedModes": [
                        {
                            "value": "Position.Up",
                            "modeResources": {
                                "friendlyNames": [
                                    {
                                        "@type": "asset",
                                        "value": {"assetId": "Alexa.Value.Open"},
                                    }
                                ]
                            },
                        },
                        {
                            "value": "Position.Down",
                            "modeResources": {
                                "friendlyNames": [
                                    {
                                        "@type": "asset",
                                        "value": {"assetId": "Alexa.Value.Close"},
                                    }
                                ]
                            },
                        },
                        {
                            "value": "Position.Stopped",
                            "modeResources": {
                                "friendlyNames": [
                                    {
                                        "@type": "text",
                                        "value": {"text": "Stopp", "locale": "de-DE"},
                                    }
                                ]
                            },
                        },
                    ],
                },
            }
        ]

    # 2. Spezialfall: RangeController (Dein Rolladen-Lift %)
    if cap == "RangeController":
        return [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.RangeController",
                "instance": "Blind.Lift",
                "version": "3",
                "properties": {
                    "supported": [{"name": "rangeValue"}],
                    "retrievable": retrievable,
                    "proactivelyReported": proactive,
                },
                "configuration": {
                    "supportedRange": {
                        "minimumValue": 0,
                        "maximumValue": 100,
                        "precision": 1,
                    },
                    "unitOfMeasure": "Alexa.Unit.Percent",
                },
            }
        ]

    if cap == "EndpointHealth":
        return [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.EndpointHealth",
                "version": "3",
                "properties": {
                    "supported": [{"name": "connectivity"}],
                    "retrievable": True,
                    "proactivelyReported": False,
                },
            }
        ]

    # 3. Standard-Mapping
    MAP = {
        "PowerController": {
            "interface": "Alexa.PowerController",
            "supported": [{"name": "powerState"}],
        },
        "ToggleController": {
            "interface": "Alexa.ToggleController",
            "supported": [{"name": "toggleState"}],
        },
        "BrightnessController": {
            "interface": "Alexa.BrightnessController",
            "supported": [{"name": "brightness"}],
        },
        "TemperatureSensor": {
            "interface": "Alexa.TemperatureSensor",
            "supported": [{"name": "temperature"}],
        },
    }

    if cap in MAP:
        config = MAP[cap]
        return [
            adr.create_payload_endpoint_capability(
                interface=config["interface"],
                supported=config["supported"],
                **prop_config,
            )
        ]

    return []

def handle_discovery():
    adr = AlexaResponse(namespace="Alexa.Discovery", name="Discover.Response")
    res = aws_dynamodb.scan(TableName=DDB_TABLE)
    devices = res.get("Items", [])
    proactive_batch = []

    for item in devices:
        did = item["device_id"]["S"]
        dname = item["device_name"]["S"]
        fname = item.get("friendly_name", {}).get("S", dname)
        isProactivelyReported = item.get("proactivelyReported", {}).get("BOOL", False)
        isRetrievable = item.get("retrievable", {}).get("BOOL", False)
        
        raw_caps = item.get("capabilities", {}).get("L", [])
        caps = [c["S"] for c in raw_caps]
        if "EndpointHealth" not in caps: caps.append("EndpointHealth")

        capabilities = [adr.create_payload_endpoint_capability()]
        for cap in caps:
            capabilities += build_capability(adr, cap, isProactivelyReported, isRetrievable)
            '''
            # Hier bauen wir die Capabilities für Discovery
            if cap == "TemperatureSensor":
                capabilities += [adr.create_payload_endpoint_capability(interface="Alexa.TemperatureSensor", supported=[{"name": "temperature"}], proactively_reported=isProactivelyReported, retrievable=isRetrievable)]
            elif cap == "PowerController":
                capabilities += [adr.create_payload_endpoint_capability(interface="Alexa.PowerController", supported=[{"name": "powerState"}], proactively_reported=isProactivelyReported, retrievable=isRetrievable)]
            elif cap == "RangeController":
                capabilities += [adr.create_payload_endpoint_capability(
                    interface="Alexa.RangeController",
                    instance="Blind.Lift", # Wichtig für Rolladen
                    supported=[{"name": "rangeValue"}],
                    proactively_reported=isProactivelyReported,
                    retrievable=isRetrievable,
                    # Hier müsstest du ggf. die adr Klasse anpassen oder manuell dicts adden
                    # wenn deine adr Klasse keine Konfiguration für Ranges unterstützt:
                )]
            elif cap == "ModeController":
                capabilities += [adr.create_payload_endpoint_capability(
                    interface="Alexa.ModeController",
                    instance="Blind.Position",
                    supported=[{"name": "mode"}],
                    proactively_reported=isProactivelyReported,
                    retrievable=isRetrievable
                )]
            elif cap == "EndpointHealth":
                capabilities += [adr.create_payload_endpoint_capability(interface="Alexa.EndpointHealth", supported=[{"name": "connectivity"}], proactively_reported=isProactivelyReported, retrievable=isRetrievable)]
            '''
        adr.add_payload_endpoint(endpoint_id=did, friendly_name=fname, display_categories=[item.get("device_category", {"S": "OTHER"})["S"]], capabilities=capabilities, manufacturer_name=MANUFACTURER_NAME)

        if isProactivelyReported:
            proactive_batch.append({"endpointId": did, "properties": get_proactive_properties(caps, item.get("state", {"S": "0"})["S"])})

    if proactive_batch:
        boto3.client('lambda').invoke(FunctionName=os.environ.get('AWS_LAMBDA_FUNCTION_NAME'), InvocationType='Event', Payload=json.dumps({"action": "internal_proactive_batch", "devices": proactive_batch, "wait_period": 5}))
    logger.info("RESPONSE: %s", json.dumps(adr.get()))
    return adr.get()

def handle_control(request):
    payload = request["directive"].get("payload", {})
    endpoint_id = request["directive"]["endpoint"]["endpointId"]
    header = request["directive"]["header"]
    namespace = header["namespace"]
    name = header["name"]
    instance = header.get("instance") # Hole die Instanz aus dem Header
    
    # Device Name für das JSON holen
    device_name = endpoint_id
    try:
        response = table.get_item(Key={'device_id': endpoint_id})
        if 'Item' in response:
            device_name = response['Item'].get('device_name', endpoint_id)
    except Exception as e:
        logger.error(f"DB Lookup failed: {e}")

    # Das JSON-Paket für openHAB
    alexa_message = {
        "endpointId": endpoint_id,
        "deviceName": device_name,
        "nameSpace": namespace,
        "requestMethod": name,
        "payload": payload
    }
    
    # Ab damit zum MQTT Broker
    iot_client.publish(
        topic="alexa",
        qos=1,
        payload=json.dumps(alexa_message)
    )

    # WICHTIG: Alexa braucht sofort eine Bestätigung (Response).
    # Da wir das Mapping in openHAB machen, schicken wir hier 
    # einfach eine generische Erfolgsmeldung zurück.
    res = AlexaResponse(
        namespace="Alexa", 
        name="Response", 
        correlation_token=header.get("correlationToken"), 
        endpoint_id=endpoint_id
    )

    res.add_context_property(
        namespace="Alexa.EndpointHealth", name="connectivity", value={"value": "OK"}
    )

    # 1. PowerController (Wert steckt im 'name', nicht im Payload!)
    if namespace == "Alexa.PowerController":
        if name == "TurnOn":
            extracted_value = "ON"
        elif name == "TurnOff":
            extracted_value = "OFF"
        res.add_context_property(
            namespace=namespace, name="powerState", value=extracted_value
        )

    # 2. ModeController (Wert steckt im Payload)
    elif namespace == "Alexa.ModeController":
        extracted_value = payload.get("mode")
        res.add_context_property(
            namespace=namespace, instance=instance, name="mode", value=extracted_value
        )

    # 3. Brightness/Range (Wert steckt im Payload)
    elif namespace == "Alexa.BrightnessController":
        extracted_value = payload.get("brightness")
        res.add_context_property(
            namespace="Alexa.BrightnessController",
            name="brightness",
            value=extracted_value,
        )

    elif namespace == "Alexa.RangeController":
        extracted_value = payload.get("rangeValue")
        res.add_context_property(
            namespace="Alexa.RangeController",
            name="rangeValue",
            instance=instance,
            value=extracted_value,
        )

    logger.info("RESPONSE:\n%s", json.dumps(res.get()))
    return res.get()


def handle_report_state(request):
    endpoint_id = request["directive"]["endpoint"]["endpointId"]
    res = table.get_item(Key={"device_id": endpoint_id}).get("Item", {})
    db_state = res.get("state", "0")
    
    response = AlexaResponse(namespace="Alexa", name="StateReport", correlation_token=request["directive"]["header"].get("correlationToken"), endpoint_id=endpoint_id)
    # Vereinfacht: Wir nehmen an, es ist ein PowerController für das Beispiel
    response.add_context_property(namespace="Alexa.PowerController", name="powerState", value="ON" if db_state in ["ON", "OPENED", "1"] else "OFF")
    return response.get()