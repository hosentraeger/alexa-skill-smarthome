import paho.mqtt.client as mqtt
import json
import ssl
import time

# --- KONFIGURATION ---
IOT_ENDPOINT = "a1mgltoxwok4cn-ats.iot.eu-west-1.amazonaws.com"
PORT = 8883
CA_FILE = "root-CA.crt"
CERT_FILE = "smarthome.cert.pem"
KEY_FILE = "smarthome.private.key"

SUB_TOPIC = "alexa/+"

# Bei paho-mqtt 2.x hat on_connect eine zusätzliche "properties" Variable
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Verbunden mit AWS IoT Core")
        client.subscribe(SUB_TOPIC)
        print(f"👂 Höre auf Topic: {SUB_TOPIC}")
    else:
        print(f"❌ Fehler beim Verbinden. Code: {rc}")

def on_message(client, userdata, msg):
    topic_parts = msg.topic.split('/')
    device_name = topic_parts[1]

    data = json.loads(msg.payload.decode())
    val = data.get("extractedValue")

    print(f"📥 Befehl für {device_name}: {val}")

    # RÜCKMELDUNG
    # Das landet dann auf "alexa/KitchenShutter/set"
    response_topic = f"alexa/{device_name}/set"
    response_payload = {
        "state": val,
        "endpointId": data.get("endpointId")
    }
    client.publish(response_topic, json.dumps(response_payload), qos=1)

# --- CLIENT SETUP ---
# Falls du paho-mqtt 2.x nutzt (was im venv wahrscheinlich ist):
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mosquitto_sub")
except AttributeError:
    # Fallback für ganz alte Versionen
    client = mqtt.Client(client_id="OpenHAB_Bridge")

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.on_connect = on_connect
client.on_message = on_message

print("🚀 Starte MQTT Bridge...")
client.connect(IOT_ENDPOINT, PORT, keepalive=60)
client.loop_forever()
