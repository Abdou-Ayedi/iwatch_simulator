import json
import paho.mqtt.client as mqtt
import time
import joblib
import numpy as np
from influxdb import InfluxDBClient
from datetime import datetime

# -------------------
# CONFIG
# -------------------
THING_ID = "org.Iotp2c/iwatch"
BROKER = "host.docker.internal"
#BROKER = "192.168.55.212"
PORT = 1883
USERNAME = "ditto"
PASSWORD = "ditto"

# -------------------
# GRAFANA SETUP
# -------------------


influx = InfluxDBClient(
    host='localhost', port=8086,
    username='admin', password='admin123',
    database='heart_data'
)

def save_to_influx(heart_rate: float, status: str, device="iwatch"):
    # status: "normal" or "anomaly"
    point = [
        {
            "measurement": "heart_rate",
            "tags": {
                "device": device,
                "status": status,              # tag for easy filtering in Grafana
            },
            "time": datetime.utcnow().isoformat() + "Z",
            "fields": {
                "value": float(heart_rate),    # numeric value for charting
                "anomaly": 1 if status == "Anomaly Detected" else 0,  # numeric flag for thresholds,
                "status_text": status
            }
        }
    ]
    influx.write_points(point)
# -------------------
# -------------------



# Topics
TOPIC_TWIN_MODIFIED = f"{THING_ID}/things/twin/events/modified"
TOPIC_LIVE_MESSAGE = f"{THING_ID}/things/twin/commands/modify"
#TOPIC_LIVE_MESSAGE = f"{THING_ID}/things/live/messages/my-message"
MODEL_PATH = "iso_forest_model.pkl"
model = joblib.load(MODEL_PATH)
print("✅ AI model loaded from", MODEL_PATH)

# -------------------
# MQTT CALLBACKS
# -------------------

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected with result code {rc}")
    # Subscribe to twin changes
    client.subscribe(TOPIC_TWIN_MODIFIED)
    print(f"📡 Subscribed to: {TOPIC_TWIN_MODIFIED}")

def on_message(client, userdata, msg):
    print(f"\n📥 Received message on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        print("⚠️ Could not decode JSON payload")
        return
    
    # Process twin changes here
    if msg.topic == TOPIC_TWIN_MODIFIED:
        handle_twin_update(payload)


def on_publish(client, userdata, mid):
    print(f"✅ Data published to {TOPIC_LIVE_MESSAGE}")

def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker with result code "+str(rc))

def handle_twin_update(data):
    print("🔄 Twin data updated:", json.dumps(data, indent=2))
    
    if 'status' in data["value"]["attributes"]['result']:
        print("✅ Result already present in attributes. Skipping update to avoid loop.")
        return
    # Extract heart rate if exists
    try:
        heart_rate = data["value"]["attributes"]["heart_rate"]
        timestamp=data["value"]["attributes"]["timestamp"]
        print(f"💓 New heart rate: {heart_rate}")

        
        prediction = model.predict(np.array([[heart_rate]]))[0]
        result = "normal" if prediction == 1 else "Anomaly Detected"

        print(f"🤖 AI Model result: {result}")
        save_to_influx(heart_rate, result)

        # Process with AI model
        #result = {"alert": "high" if heart_rate > 100 else "normal"}
        ditto_data = {
        "topic": "org.Iotp2c/iwatch/things/twin/commands/modify",
        "path": "/",
        "value":{
          "thingId":"org.Iotp2c:iwatch",
          "policyId":"org.Iotp2c:policy",
          "definition":"http://192.168.1.98:8000/iwatch.tm.jsonld",
                "attributes":{
                    "heart_rate":heart_rate,
                    "timestamp":timestamp,
                    "longitude":-122.41938999999999,
                    "latitude":37.774910000000006,
                    "result": {"status": result}
                    
                }
        }
    }
        # Send result back to Ditto
        publish_result(ditto_data)
    except KeyError:
        print("⚠️ heart_rate not found in update")

def publish_result(result):
    result_json = json.dumps(result)
    client.publish(TOPIC_LIVE_MESSAGE, payload=result_json, qos=0)
    print(f"📤 Sent result to {TOPIC_LIVE_MESSAGE}: {result_json}")

# -------------------
# MQTT CLIENT SETUP
# -------------------

client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish
client.on_disconnect = on_disconnect

client.connect(BROKER, PORT, 60)
client.loop_start()
#client.loop_forever()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("⛔ Stopping...")
    client.loop_stop()
    client.disconnect()
