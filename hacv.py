#
# Example integration of using the keras-yolo3 object detection.
# This integration is towards MQTT in Home-Assistant and can easily
# be configured to provide both images of detection and notifications
# via speakers / TTS - and also be used for triggering other automations
# (via binary sensor API over MQTT).
#
# Author: Joakim Eriksson, joakim.eriksson@ri.se
#

import paho.mqtt.client as mqttClient
import threading, time, yaml

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker:", rc)
    else:
        print("Connection failed: ", rc)

class CVMQTTPlugin:
    client = None
    timer = None
    name = "area"
    detects = {}

    def __init__(self, cfg):
        if cfg is None:
            raise Exception('You must load a config file')
        broker_address = cfg['hacv']['host']
        self.name = cfg['hacv']['name']

        self.binary_sensor_topic = "homeassistant/binary_sensor/" + self.name
        self.binary_sensor_state_topic = self.binary_sensor_topic + "/state"
        self.camera_topic = f"homeassistant/camera/" + self.name
        self.sensor_topic = "homeassistant/sensor/" + self.name
        self.sensor_state_topic = self.sensor_topic + "/state"
        self.tts_topic = "homeassistant/tts/say/" + self.name
            
        self.client = mqttClient.Client("Python-CV-YOLO3-" + self.name)
        self.client.on_connect = on_connect
        self.client.connect(broker_address)
        self.client.loop_start()
        self.publish_config()

    def publish_config(self):
        bsname = self.name + " Motion"
        self.client.publish(
            self.binary_sensor_topic + "/config",
            str({"name": bsname, "unique_id": bsname, "device_class": "motion", "state_topic": self.binary_sensor_state_topic})
        )
        cname = self.name + " Detector"
        self.client.publish(
            self.camera_topic + "/config",
            str({"name": cname, "unique_id": cname, "topic": self.camera_topic})
        )
        sname = self.name + " Detector"
        self.client.publish(
            self.sensor_topic + "/config",
            str({"name": sname, "unique_id": sname, "state_topic": self.sensor_state_topic})
        )

    def no_motion(self):
        print("publishing motion OFF")
        self.client.publish(self.binary_sensor_state_topic, 'OFF')
        print("publishing")

    def publish_detection(self, detection_type, likelihood):
        print("Publishing ", detection_type, likelihood)
        if detection_type not in self.detects:
            self.detects[detection_type] = 0
        if self.detects[detection_type] + 10.0 < time.time():
            self.detects[detection_type] = time.time()
            print("publish TTS")
            self.client.publish(self.tts_topic, "The camera viewing " + self.name + " can see a " + detection_type)
            print("publish motion ON")
            self.client.publish(self.binary_sensor_state_topic, 'ON')
            print("publish detection")
            self.client.publish(self.sensor_state_topic, detection_type)
            if self.timer is not None:
                self.timer.cancel()
            print("Setting up timer for 10 seconds")
            self.timer = threading.Timer(10, self.no_motion)
            self.timer.start()

    def publish_image(self, image):
        print("Publishing image.")
        self.client.publish(self.camera_topic, image)

    def __del__(self):
        self.client.disconnect()
        self.client.loop_stop()

