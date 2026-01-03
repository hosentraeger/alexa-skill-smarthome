#!/bin/bash

# Konfiguration
SKILL_DIR="alexa-skill-smarthome/src"
MQTT_DIR="alexa-device-update-state-mqtt/src"
DEVICES_DIR="alexa-devices/src"
COMMON_FILES=("alexa_device.py" "alexa_utils.py" "alexa_auth.py" "alexa_response.py" "alexa_discovery.py")
CONTROLLERS_DIR="controllers"

# AWS Lambda Funktionsnamen
SKILL_LAMBDA_NAME="alexa-skill-smarthome"
MQTT_LAMBDA_NAME="alexa-device-update-state-mqtt"
DEVICES_LAMBDA_NAME="alexa-devices"

# 1. Gemeinsame Dateien kopieren
echo "--- Synchronisiere gemeinsame Dateien ---"
for file in "${COMMON_FILES[@]}"; do
    if [ -f "$SKILL_DIR/$file" ]; then
        cp "$SKILL_DIR/$file" "$MQTT_DIR/"
    fi
done

# Controller-Ordner synchronisieren OHNE Pycache
rsync -av --delete --exclude "__pycache__" "$SKILL_DIR/$CONTROLLERS_DIR/" "$MQTT_DIR/$CONTROLLERS_DIR/"

# 2. Deployment Funktion
deploy_lambda() {
    local dir=$1
    local name=$2
    echo "--- Erstelle Paket für $name ---"
    
    # In das Verzeichnis wechseln
    pushd "$dir" > /dev/null || exit
    
    # Altes Zip löschen falls vorhanden
    rm -f ../deploy.zip
    
    # ZIP erstellen: Wir ignorieren alles Unnötige
    zip -r ../deploy.zip . -x "*.git*" "*tests*" "*__pycache__*" "*.pyc" "old_*" "*.swp"
    
    echo "--- Upload zu AWS ($name) ---"
    aws lambda update-function-code --function-name "$name" --zip-file fileb://../deploy.zip
    
    # Zurück zum Startordner
    popd > /dev/null
}

case "$1" in
    skill) deploy_lambda "$SKILL_DIR" "$SKILL_LAMBDA_NAME" ;;
    mqtt)  deploy_lambda "$MQTT_DIR" "$MQTT_LAMBDA_NAME" ;;
    devices)  deploy_lambda "$DEVICES_DIR" "$DEVICES_LAMBDA_NAME" ;;
    *)
        echo "Usage: $0 {skill|mqtt|devices}"
        exit 1
esac

echo "--- Deployment abgeschlossen ---"