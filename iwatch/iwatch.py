import paho.mqtt.client as mqtt
import json
import iwatch_simulator
import time
import requests
import os
import csv
from kafka import KafkaProducer

import copy
import socket

# Thing ID and topics
THING_ID = "org.Iotp2c/iwatch"
MQTT_TOPIC = f"{THING_ID}/things/twin/commands/modify"
SUBSCRIBE_TOPIC = f"{THING_ID}/things/twin/events/modified"

MQTT_BROKER = "host.docker.internal"  # Change if needed
#MQTT_BROKER = "192.168.1.98"  # Change if needed
#MQTT_BROKER = "localhost"  # Change if needed
#MQTT_BROKER = socket.gethostbyname("mosquitto")  # Change if needed
MQTT_PORT = 1883
USERNAME = "ditto"
PASSWORD = "ditto"

def save_data_to_csv(data, filename="iwatch_data_1.csv"):
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as csv_file:
        fieldnames = ['heart_rate', 'timestamp', 'longitude', 'latitude','result']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()  # Write header if file is new

        writer.writerow({
            'heart_rate': data['heart_rate'],
            'timestamp': data['timestamp'],
            'longitude': data['longitude'],
            'latitude': data['latitude'],
            "result": data['result']

        })


def configure_outbound_mapping():
    url = "http://localhost:8080/api/2/connections/my-mqtt-outbound"
    auth = ('ditto', 'ditto')

    payload = {
        "targets": [
            {
                "address": "org.Iotp2c/iwatch/things/twin/events/modified",
                "topics": ["things/live/messages/my-message"],
                "authorizationContext": []
            }
        ],
        "source": {
            "type": "things",
            "topics": ["things/twin/events", "things/live/commands"]
        },
        "protocol": {
            "type": "mqtt",
            "uri": "tcp://ditto:ditto@host.docker.internal:1883",
            "clientId": "ditto-connection"
        },
        "enabled": True
    }

    response = requests.put(url, auth=auth, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
    print(response.status_code, response.text)
    #if response.status_code in [200, 201]:
        #print("✅ Outbound mapping configured successfully!")
    #else:
        #print(f"❌ Failed to configure outbound mapping. Status: {response.status_code}, Response: {response.text}")


configure_outbound_mapping()





# Setup MQTT client globally so we can reuse it
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)

# Callback: when connected
def on_connect(client, userdata, flags, rc):
    print("✅ Connected with result code " + str(rc))
    client.subscribe(SUBSCRIBE_TOPIC)
    print(f"🔔 Subscribed to topic: {SUBSCRIBE_TOPIC}")

# Callback: when a message is received
def on_message(client, userdata, msg):
    print("\n📩📩📩 Message received from Ditto:📩📩📩")
    payload = json.loads(msg.payload.decode())
    print(f"Raw Payload: {payload}")
    ######################################
    attributes = payload['value']['attributes']
    heart_rate = attributes['heart_rate']
    print(f"Received heart rate: {heart_rate}")
    
    

# Callback: when published
def on_publish(client, userdata, mid):
    print(f"✅ Data published to {MQTT_TOPIC}")
    
def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker with result code "+str(rc))

# Set callbacks
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish
client.on_disconnect = on_disconnect

# Get the IP address of the MQTT broker
    #broker_ip = socket.gethostbyname("mosquitto")
    #broker_ip = "localhost"
#broker_ip = "host.docker.internal" 


def send_data_to_ditto(iwatch_data):

    
    # Prepare the Ditto command payload
    ditto_data = {
        "topic": "org.Iotp2c/iwatch/things/twin/commands/modify",
        "path": "/",
        "value":{
          "thingId":"org.Iotp2c:iwatch",
          "policyId":"org.Iotp2c:policy",
          "definition":"http://192.168.1.98:8000/iwatch.tm.jsonld",
                "attributes":{
                    "heart_rate":iwatch_data['heart_rate'],
                    "timestamp":iwatch_data['timestamp'],
                    "longitude":iwatch_data['longitude'],
                    "latitude":iwatch_data['latitude'],
                    "result": iwatch_data['result']
                    
                }
        }
    }
    # Convert the dictionary to a JSON string http://192.168.1.98:8000/iwatch.tm.jsonld
    ditto_data_str = json.dumps(ditto_data)

    # Publish the message to the MQTT topic
    client.publish(MQTT_TOPIC, payload=ditto_data_str)

    # Disconnect from the MQTT broker

    print("Data sent to Ditto: " + json.dumps(ditto_data))
    save_data_to_csv(iwatch_data)

# Connect to the MQTT broker
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

properties = ['heart_rate', 'timestamp', 'longitude', 'latitude','result']
dict_dt = {property: None for property in properties}
# Example usage
#while True:
#for i in range(4):
iwatch_data = next(iwatch_simulator.iwatch(dict_dt))
send_data_to_ditto(iwatch_data)
    #time.sleep(1)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("⛔ Stopping...")
    client.loop_stop()
    client.disconnect()