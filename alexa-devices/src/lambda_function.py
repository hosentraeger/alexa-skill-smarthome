import json
import os
# Importiere deine Logik-Files
from alexa_device_add import add_device
from alexa_device_update import update_device 
from alexa_devices_list import list_devices
from alexa_device_delete import delete_device

def lambda_handler(event, context):
    method = event.get("httpMethod")
    
    try:
        if method == "GET":
            return list_devices(event)
        elif method == "POST":
            return add_device(event)
        elif method in ["PATCH", "PUT"]:
            return update_device(event)
        elif method == "DELETE":
            return delete_device(event)
        
        # Falls keine Methode passt
        return {
            "statusCode": 405, 
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Method {method} not allowed"})
        }
        
    except Exception as e:
        # Dieser Block muss auf der gleichen Ebene wie 'try' stehen!
        print(f"Fehler: {str(e)}")
        return {
            "statusCode": 500, 
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }