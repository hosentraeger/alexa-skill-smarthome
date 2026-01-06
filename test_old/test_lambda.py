#!/usr/bin/env python3

# tests/test_lambda.py

import json
import sys
import os

# Den Pfad zum Root-Verzeichnis (ein Level über /tests) hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    # Jetzt findet Python die lambda_function im Root
    from lambda_function import lambda_handler
except ImportError as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

def main():
    # 1. Prüfen, ob Daten via Pipe kommen
    if sys.stdin.isatty():
        print("Benutzung: echo '<json>' | python3 test_lambda.py")
        return

    # 2. JSON von stdin lesen
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Ungültiges JSON empfangen: {e}")
        return

    # 3. Einen leeren Lambda-Context simulieren
    class MockContext:
        def __init__(self):
            self.function_name = "alexa_smart_home_local_test"
            self.memory_limit_in_mb = 128
            self.invoked_function_arn = "arn:aws:lambda:local:123456789:function:test"
            self.aws_request_id = "local-test-id"

    # 4. Den echten Handler aufrufen
    print("\n--- LAMBDA EXECUTION START ---")
    try:
        response = lambda_handler(event, MockContext())
        
        # 5. Die Antwort formatiert ausgeben
        print("\n--- LAMBDA RESPONSE ---")
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"\nCRITICAL ERROR während der Ausführung: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- LAMBDA EXECUTION END ---")

if __name__ == "__main__":
    main()

'''
DISCOVERY
echo '{
  "directive": {
    "header": {
      "namespace": "Alexa.Discovery",
      "name": "Discover",
      "payloadVersion": "3",
      "messageId": "123"
    },
    "payload": {
      "scope": { "type": "BearerToken", "token": "access-token-from-skill" }
    }
  }
}' | python3 tests/test_lambda.py


CONTROL POWERCONTROLLER
echo '{
  "directive": {
    "header": {
      "namespace": "Alexa.PowerController",
      "name": "TurnOn",
      "payloadVersion": "3",
      "messageId": "msg-001",
      "correlationToken": "dG9rZW4tMDAx"
    },
    "endpoint": {
      "endpointId": "79894485-e5d5-4d3d-a0e3-6aa9f19b2967",
      "scope": { "type": "BearerToken", "token": "access-token" }
    },
    "payload": {}
  }
}' | python3 tests/test_lambda.py


CONTROL ROLLERSHUTTERCONTROLLER
echo '{
  "directive": {
    "header": {
      "namespace": "Alexa.ModeController",
      "name": "SetMode",
      "payloadVersion": "3",
      "messageId": "msg-002",
      "correlationToken": "dG9rZW4tMDAy"
    },
    "endpoint": {
      "endpointId": "3857df88-d875-49c5-85ae-58487127cb0d",
      "scope": { "type": "BearerToken", "token": "access-token" }
    },
    "payload": {
      "mode": "Position.Down"
    }
  }
}' | python3 tests/test_lambda.py
'''