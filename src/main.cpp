#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <ArduinoJson.h>

const char* ssid = "SPACER";
const char* password = "11111111";
const char* mqtt_server = "172.20.10.8";

#define I2C_SDA 4
#define I2C_SCL 5
#define MIC_PIN 6
#define FALL_THRESHOLD 2  // G-Force
#define MIC_THRESHOLD 500  // Abnormal sound level


Adafruit_MPU6050 mpu;
WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    String clientId = "ElderSafe";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);

  // Init MPU6050
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) delay(10);
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  /* --- 1. Read Sensor --- */
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  float svm = sqrt(sq(a.acceleration.x) + sq(a.acceleration.y) + sq(a.acceleration.z));
  float g_force = svm / 9.8; 
  int micValue = analogRead(MIC_PIN);


/* --- 2. Send general data (Heartbeat) every 1 second --- */
  static unsigned long lastMsg = 0;
  unsigned long now = millis();
  if (now - lastMsg > 1000) {
    lastMsg = now;
    
    // Send general Motion data
    JsonDocument doc;
    doc["g_force"] = g_force;
    doc["mic"] = micValue;

    char buffer[256];
    serializeJson(doc, buffer);

    Serial.print("G Force: "); 
    Serial.print(g_force);
    Serial.print(" Mic: "); 
    Serial.println(micValue);

    // Publish to Topic: elder/sensor/motion
    client.publish("elder/sensor/motion", buffer);
    Serial.print("Sent MQTT: "); 
    Serial.println(g_force);
  }
}
