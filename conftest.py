import sys
import os
import pytest

# Pfade sofort setzen, nicht erst in einer Fixture!
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
paths = [
    os.path.join(BASE_DIR, 'alexa-skill-smarthome', 'src'),
    os.path.join(BASE_DIR, 'alexa-device-update-state-mqtt', 'src')
]

for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

# Die URL setzen [cite: 2026-01-03]
os.environ["ALEXA_EVENTS_URL"] = "https://api.eu.amazonalexa.com/v3/events"