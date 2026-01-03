# alexa_auth.py

import urllib.request
import urllib.parse
import json
import logging
import uuid
import boto3
import os

logger = logging.getLogger()
ssm = boto3.client("ssm")

CLIENT_ID = os.environ.get("ALEXA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ALEXA_CLIENT_SECRET")

def handle_accept_grant(request):
    """Verarbeitet den Alexa.Authorization / AcceptGrant Request."""
    payload = request.get("directive", {}).get("payload", {})
    grant_code = payload.get("grant", {}).get("code")
    
    if not grant_code:
        logger.error("AcceptGrant fehlgeschlagen: Kein grant_code vorhanden.")
        return {"error": "no_grant_code"}

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
                ssm.put_parameter(
                    Name="/alexa/refresh_token", 
                    Value=refresh_token, 
                    Type="SecureString", 
                    Overwrite=True
                )
                logger.info("ERFOLG: Refresh Token in SSM gespeichert.")
    except Exception as e:
        logger.error(f"Amazon Auth API Fehler: {str(e)}")
        # In der Produktivphase sollte hier ein Error-Event an Alexa zurückgehen

    # Die Antwort auf AcceptGrant ist immer ein leeres Payload
    return {
        "event": {
            "header": {
                "namespace": "Alexa.Authorization",
                "name": "AcceptGrant.Response",
                "messageId": str(uuid.uuid4()),
                "payloadVersion": "3"
            },
            "payload": {}
        }
    }