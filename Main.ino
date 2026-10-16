#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <BH1750.h>
#include <LiquidCrystal_I2C.h>

// =====================================================
// PINS
// =====================================================

#define SDA_PIN 21
#define SCL_PIN 22

#define SOIL_PIN 34

#define RED_PIN 25
#define GREEN_PIN 26
#define BLUE_PIN 27

// =====================================================
// WIFI
// =====================================================

const char* WIFI_SSID = "A";
const char* WIFI_PASSWORD = "qdd5t5cspaqyhyk";

// =====================================================
// TIME / NTP
// =====================================================

const char* NTP_SERVER = "pool.ntp.org";

const long GMT_OFFSET_SEC = 0;
const int DAYLIGHT_OFFSET_SEC = 0;

bool timeSynchronized = false;

unsigned long lastTimeCheck = 0;

const unsigned long TIME_CHECK_INTERVAL = 1000;

// =====================================================
// AWS IoT
// =====================================================

const char* AWS_IOT_ENDPOINT =
    "a1nrnv5x66u1mb-ats.iot.us-east-1.amazonaws.com";

const char* MQTT_CLIENT_ID =
    "GreenPulse-01";

const char* SENSOR_TOPIC =
    "greenpulse/device01/sensors";

const char* CARE_TOPIC =
    "greenpulse/device01/care";

const char* STATUS_TOPIC = "greenpulse/device01/status";

// =====================================================
// AWS CERTIFICATES
// =====================================================

const char* AMAZON_ROOT_CA = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv
b3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj
ca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM
9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw
IFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6
VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L
93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm
jgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC
AYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA
A4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI
U5PMCCjjmCXPI6T53iHTfIUJrU6adTrCC2qJeHZERxhlbI1Bjjt/msv0tadQ1wUs
N+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V8viTO96LXFvKWlJbYK8U90vv
o/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJcJmApzyMZFo6IQ6XU
5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeXeGADbkpy
rqXRfboQnoZsG4q5WTP468SQvvG5
-----END CERTIFICATE-----
)EOF";

const char* DEVICE_CERTIFICATE = R"KEY(
-----BEGIN CERTIFICATE-----
MIIDWTCCAkGgAwIBAgIUZ2tmhxLdE0wYMJbIzmExGrTOaoYwDQYJKoZIhvcNAQEL
BQAwTTFLMEkGA1UECwxCQW1hem9uIFdlYiBTZXJ2aWNlcyBPPUFtYXpvbi5jb20g
SW5jLiBMPVNlYXR0bGUgU1Q9V2FzaGluZ3RvbiBDPVVTMB4XDTI2MTAwNTE2NTMz
NVoXDTQ5MTIzMTIzNTk1OVowHjEcMBoGA1UEAwwTQVdTIElvVCBDZXJ0aWZpY2F0
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMhKOc4ym8M7cAPVj2xz
+7QSAnI/K57eHx+W3HZTy2IhggvDFPIYeqbj0Ei40OrZlRSdemFg2gFvIHwl8/uq
KOIBeQUYbwwnfQ0fVGfmNsOgX8kP98beVa9woBzm8PzMloxlcwx4QZ3pFVCqFm2P
MgO4bO9LQ2jjqM86r5yfytTyx9dCXFTzajsybNvvBbpOjL41uYwJhhlqYfp1jng+
S4NcxWuwzD3l1q2/jJabNcPFbo9i8rE/UrnWUrMclw1rseKUysjxLay+L9w9arwa
QWbLJrpGkTdNeJBbht4PrW5NVF0VPRrJz1ieNL58Lv2Lne5kSYyS6NaMdA0UYsc7
1DECAwEAAaNgMF4wHwYDVR0jBBgwFoAU8Cqsl9E6MU/BN8ehW+1+PqyKI98wHQYD
VR0OBBYEFJObzbbDVCCreFi6j/3zDOgeT4nnMAwGA1UdEwEB/wQCMAAwDgYDVR0P
AQH/BAQDAgeAMA0GCSqGSIb3DQEBCwUAA4IBAQCdkogFV54WuEcn063QMX/0uUNr
MhByssyaUAZ0g60wHI6coGt569WCEB041mwAOHvkslrvWxcuveix844zEBkbwEVx
GHdb+9byJxnYvjXA6hTsXULBjd/iiu/TGD0y8r8Lpm3HOQjhdPCY5kaBdWs9H1DB
FjP4fEdhnCPywZZo/eFWcNyhadUgX0oDlRxCS1X0TiIY/OJ72awsGn9KLK8KtHoo
uGFdSPt3uSRFo/4cohtruZrItyt6iutYNzIt1hkLX3gaRXtQz0WjHezXcVEbcmUN
tS7JSdfohjVkbV5AxctEZT2dRFdrIxJ8Aopre0bX4FCVhXooA27Wt8neK6QP
-----END CERTIFICATE-----
)KEY";

const char* PRIVATE_KEY = R"KEY(
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAyEo5zjKbwztwA9WPbHP7tBICcj8rnt4fH5bcdlPLYiGCC8MU
8hh6puPQSLjQ6tmVFJ16YWDaAW8gfCXz+6oo4gF5BRhvDCd9DR9UZ+Y2w6BfyQ/3
xt5Vr3CgHObw/MyWjGVzDHhBnekVUKoWbY8yA7hs70tDaOOozzqvnJ/K1PLH10Jc
VPNqOzJs2+8Fuk6MvjW5jAmGGWph+nWOeD5Lg1zFa7DMPeXWrb+Mlps1w8Vuj2Ly
sT9SudZSsxyXDWux4pTKyPEtrL4v3D1qvBpBZssmukaRN014kFuG3g+tbk1UXRU9
GsnPWJ40vnwu/Yud7mRJjJLo1ox0DRRixzvUMQIDAQABAoIBAQCn+wDSPEXBDvea
b6Fzby76TmR41xxJiLeHsepC33JjYgEExl+pz/gGQmjspPyrC0NqX81FIIqWy1Hu
bZJcTtEtA9kw+dYg1nmd6NnMrhreJYJQSjEgPFaW5pmSw+n3y8q0A13jZnR58QOs
fIqE5qUm06WhaHkn3lA1RV4FuUrPHzaeBKBAwM7u+yEmokniI2fmO4k4ZCIaus1r
2Q6Cotq2q2OOBrePhCwTadE/V3O5v5DqYGuCS0Fdp+nYt/95kokp89flQ6Mhj+S2
MLq2cgGPc/Tghu5VeOMQWvNJ+/58Wto47V5T3gbEdLYSNCEpZ42w+Mwv+bFFhW2O
a3G91b4BAoGBAPSwdcGYt9QOkaAAtDxbnaQKLdUGkP8KcbFrNo7GGX+7+AJGg3fD
fKUFR+aM3fDm9eum3mzVKlTNn+xogBtl6HcH8MFtbo5JcVphqBsjBAN6tudPtLnE
LsPS3BVSkb+KSH+rxdfndCXeXOH8BkQTwN7eI/rqQzKVMVKB5lrR50LhAoGBANGM
XUnoN85h025vj1iO8QYrF+cvkOl3tvBdSZQ5q8AYbKo/uA0ZysjgF66jxOvEowKr
Lm3qsZaXdC8Kh4E0FLL5PsdB8VRrcPv1c3ElLT/87ELvY4cpYsl4PGZ8/xWfThht
hHBBoHowB+cuTLYAX3b+0g3J4KJDp03iRURDMAtRAoGAOEyNm5Cu4zzC5uSik6yk
tcSdzQDoxbW6eQ7pC6qq3Uf7hVKCF0FEYZe4dmR9AFuzw5euX64gQkjZfgSBTUyC
UzjhfS/XmydszFXh3vSMjNxkTw54z7FC7U2L0+AepsqDadS0/btEbx4dkuVw76L3
4o+MCcRy16WaJpi6zrSzGCECgYB2X9K7U4FjBwRHmKHjpywlDeb85HP6T3R6qFhO
cZ3CcInCSyiPzgguHdmDAGTXw0dK1KTv1urnZTtu74XIyUEAMajzKx9HT0KOMwQ5
4ISFZz2YOl+BFTIHGfMU+nunHU0io4tzVr9vBv8P66nODrvfHuhOfcJ2J721U6NJ
gqL7YQKBgDnVU8jj2wlihxT0EwN+3b27uX9fEKk6ahoqKxNrTPkRx72R8ogkwLaY
PhF7YemA58lw1PwkA+hyuLZLxCH8HadtKUgInMlEUfNxq8FvkGqmhrgmxpAyKPuX
HA+fRuJMMW/YVFKVopKHgho/8kk46UDIXNFae4jEDWK/B4NGWUVJ
-----END RSA PRIVATE KEY-----
)KEY";

// =====================================================
// LCD SCREEN CONTROL
// =====================================================

int currentScreen = 0;

unsigned long lastScreenChange = 0;

const unsigned long SCREEN_INTERVAL = 3000;

// Latest sensor values
float currentTemperature = 0;
float currentHumidity = 0;
int currentSoilPercentage = 0;
float currentLux = 0;



// =====================================================
// SENSOR OBJECTS
// =====================================================

Adafruit_BME280 bme;
BH1750 lightMeter;

LiquidCrystal_I2C lcd(0x27, 16, 2);

// =====================================================
// MQTT
// =====================================================

WiFiClientSecure secureClient;
PubSubClient mqttClient(secureClient);

// =====================================================
// SENSOR STATUS
// =====================================================

bool bmeOK = false;
bool lightOK = false;

// Soil calibration values
const int SOIL_DRY = 3200;
const int SOIL_WET = 1400;

// =====================================================
// RGB
// =====================================================

void setRGB(int red, int green, int blue) {

  analogWrite(RED_PIN, red);
  analogWrite(GREEN_PIN, green);
  analogWrite(BLUE_PIN, blue);
}

void updateRGB(int soilPercentage) {

  if (soilPercentage >= 40) {
    // GREEN - favorable
    setRGB(0, 255, 0);

  } else if (soilPercentage >= 25) {
    // YELLOW - moderate
    setRGB(255, 255, 0);

  } else {
    // RED - critical
    setRGB(255, 0, 0);
  }
}

// =====================================================
// RGB ERROR STATUS INDICATORS
// =====================================================

unsigned long lastLEDBlink = 0;

const unsigned long LED_BLINK_INTERVAL = 500;

bool ledBlinkState = false;

// =====================================================
// RGB STATUS PRIORITY
// =====================================================

void updateLEDStatus() {

  // Priority 1: Sensor error -> BLINK RED
  if (!bmeOK || !lightOK) {

    if (millis() - lastLEDBlink >= LED_BLINK_INTERVAL) {
      lastLEDBlink = millis();
      ledBlinkState = !ledBlinkState;
    }

    if (ledBlinkState) {
      setRGB(255, 0, 0);
    } else {
      setRGB(0, 0, 0);
    }

  }

  // Priority 2: MQTT disconnected -> BLINK BLUE
  else if (!mqttClient.connected()) {

    if (millis() - lastLEDBlink >= LED_BLINK_INTERVAL) {
      lastLEDBlink = millis();
      ledBlinkState = !ledBlinkState;
    }

    if (ledBlinkState) {
      setRGB(0, 0, 255);
    } else {
      setRGB(0, 0, 0);
    }

  }

  // Priority 3: Normal operation -> Soil moisture indication
  else {

    ledBlinkState = false;
    lastLEDBlink = millis();

    updateRGB(currentSoilPercentage);

  }
}

void updateLCD() {

  lcd.clear();

  // =========================================
  // PRIORITY 1: SENSOR ERRORS
  // =========================================

  if (!bmeOK || !lightOK) {

    lcd.setCursor(0, 0);
    lcd.print("SENSOR ERROR!");

    lcd.setCursor(0, 1);

    if (!bmeOK && !lightOK) {
      lcd.print("Check Sensors");
    }
    else if (!bmeOK) {
      lcd.print("Check Temp");
    }
    else {
      lcd.print("Check Light");
    }

    return;
  }

  // =========================================
  // PRIORITY 2: MQTT DISCONNECTED
  // =========================================

  if (!mqttClient.connected()) {

    lcd.setCursor(0, 0);
    lcd.print("MQTT: OFFLINE");

    lcd.setCursor(0, 1);
    lcd.print("Reconnecting...");

    return;
  }

  // =========================================
  // NORMAL OPERATION
  // =========================================

  if (currentScreen == 0) {

    lcd.setCursor(0, 0);

    lcd.print("T:");
    lcd.print(currentTemperature, 1);
    lcd.print("C ");

    lcd.print("H:");
    lcd.print(currentHumidity, 0);
    lcd.print("%");

    lcd.setCursor(0, 1);
    lcd.print("Temp / Humidity");

  }

  else if (currentScreen == 1) {

    lcd.setCursor(0, 0);

    lcd.print("Soil:");
    lcd.print(currentSoilPercentage);
    lcd.print("%");

    lcd.print(" L:");
    lcd.print(currentLux, 0);

    lcd.setCursor(0, 1);
    lcd.print("Moisture / Light");

  }

  else if (currentScreen == 2) {

    lcd.setCursor(0, 0);
    lcd.print("MQTT: CONNECTED");

    lcd.setCursor(0, 1);
    lcd.print("AWS IoT Core");

  }
}

// =====================================================
// WIFI
// =====================================================


// =====================================================
// NON-BLOCKING WIFI CONNECTION
// =====================================================

unsigned long lastWiFiAttempt = 0;
const unsigned long WIFI_RECONNECT_INTERVAL = 10000;

void connectWiFi() {

  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  if (millis() - lastWiFiAttempt < WIFI_RECONNECT_INTERVAL) {
    return;
  }

  lastWiFiAttempt = millis();

  Serial.println("Attempting Wi-Fi connection...");

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}



String getTimestamp() {

  struct tm timeInfo;

  if (!getLocalTime(&timeInfo)) {
    return "TIME_ERROR";
  }

  char timestamp[25];

  strftime(
    timestamp,
    sizeof(timestamp),
    "%Y-%m-%dT%H:%M:%SZ",
    &timeInfo
  );

  return String(timestamp);
}

// =====================================================
// MQTT CALLBACK
// =====================================================

void mqttCallback(char* topic, byte* payload, unsigned int length) {

  
  Serial.print("Message received on: ");
  Serial.println(topic);

  Serial.println();
  Serial.println("========== MQTT MESSAGE ==========");

  Serial.print("Topic: ");
  Serial.println(topic);

  Serial.print("Message: ");

  for (unsigned int i = 0; i < length; i++) {

    Serial.print((char)payload[i]);
  }

  Serial.println();
  Serial.println("==================================");
}

// =====================================================
// MQTT CONNECTION
// =====================================================


// =====================================================
// NON-BLOCKING MQTT CONNECTION
// =====================================================

unsigned long lastMQTTAttempt = 0;
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;

void connectMQTT() {

  // Do not attempt reconnection while Wi-Fi is disconnected.
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  // Do not reconnect if MQTT is already connected.
  if (mqttClient.connected()) {
    return;
  }

  // Wait between reconnection attempts.
  if (millis() - lastMQTTAttempt < MQTT_RECONNECT_INTERVAL) {
    return;
  }

  lastMQTTAttempt = millis();

  Serial.println("Attempting MQTT connection...");

  const char* willMessage =
      "{\"device_id\":\"greenpulse-01\",\"status\":\"offline\"}";

  if (mqttClient.connect(
        MQTT_CLIENT_ID,
        STATUS_TOPIC,
        1,
        false,
        willMessage
      )) {

    Serial.println("AWS IoT MQTT connected!");

    const char* onlineMessage =
        "{\"device_id\":\"greenpulse-01\",\"status\":\"online\"}";

    mqttClient.publish(
        STATUS_TOPIC,
        onlineMessage,
        false
    );

    mqttClient.subscribe(CARE_TOPIC);
    mqttClient.subscribe(STATUS_TOPIC);

    Serial.println("MQTT subscriptions restored.");

  } else {

    Serial.print("MQTT connection failed. State: ");
    Serial.println(mqttClient.state());

  }
}

// =====================================================
// CHECK NTP TIME SYNCHRONIZATION
// =====================================================

void checkTimeSynchronization() {

  if (timeSynchronized) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  if (millis() - lastTimeCheck < TIME_CHECK_INTERVAL) {
    return;
  }

  lastTimeCheck = millis();

  struct tm timeInfo;

  if (getLocalTime(&timeInfo, 10)) {

    // Reject obviously invalid dates.
    if (timeInfo.tm_year >= (2024 - 1900)) {

      timeSynchronized = true;

      Serial.println("NTP time synchronized successfully!");

      Serial.print("UTC time: ");
      Serial.println(getTimestamp());

    }

  } else {

    Serial.println("Waiting for NTP time...");

  }
}



// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("==================================");
  Serial.println("       GREENPULSE STARTING        ");
  Serial.println("==================================");

  // ---------------------------------------------------
  // Pins
  // ---------------------------------------------------

  pinMode(SOIL_PIN, INPUT);

  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);

  setRGB(0, 0, 0);

  // ---------------------------------------------------
  // I2C
  // ---------------------------------------------------

  Wire.begin(SDA_PIN, SCL_PIN);

  // ---------------------------------------------------
  // LCD
  // ---------------------------------------------------

  lcd.init();

  lcd.backlight();

  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("GreenPulse");

  lcd.setCursor(0, 1);
  lcd.print("Starting...");

  delay(2000);

  // ---------------------------------------------------
  // BME280
  // ---------------------------------------------------

  if (bme.begin(0x76)) {

    bmeOK = true;

    Serial.println("BME280 found at 0x76");

  } else if (bme.begin(0x77)) {

    bmeOK = true;

    Serial.println("BME280 found at 0x77");

  } else {

    Serial.println("BME280 NOT FOUND!");
  }

  // ---------------------------------------------------
  // BH1750
  // ---------------------------------------------------

  if (lightMeter.begin(
        BH1750::CONTINUOUS_HIGH_RES_MODE)) {

    lightOK = true;

    Serial.println("BH1750 found");

  } else {

    Serial.println("BH1750 NOT FOUND!");
  }

  // ---------------------------------------------------
  // Wi-Fi
  // ---------------------------------------------------

  connectWiFi();

// ===================================================
// NTP TIME CONFIGURATION
// ===================================================

Serial.println();
Serial.println("Configuring NTP time...");

configTime(
    GMT_OFFSET_SEC,
    DAYLIGHT_OFFSET_SEC,
    NTP_SERVER
);

Serial.println("NTP configured.");
Serial.println("Time synchronization will be checked in loop().");

  // ---------------------------------------------------
  // TLS
  // ---------------------------------------------------

  Serial.println();
  Serial.println("Configuring TLS...");

  secureClient.setCACert(AMAZON_ROOT_CA);

  secureClient.setCertificate(DEVICE_CERTIFICATE);

  secureClient.setPrivateKey(PRIVATE_KEY);

  // ---------------------------------------------------
  // MQTT
  // ---------------------------------------------------

  mqttClient.setServer(
      AWS_IOT_ENDPOINT,
      8883);

  mqttClient.setCallback(mqttCallback);

  mqttClient.setBufferSize(1024);

  connectMQTT();

  updateLCD();
  lastScreenChange = millis();
}

// =====================================================
// LOOP
// =====================================================

void loop() { 
  
  // ======== // MAINTAIN WIFI WITHOUT BLOCKING // ======== 
connectWiFi();

// ==== // MAINTAIN MQTT WITHOUT BLOCKING // ======= 
connectMQTT();

// Process incoming MQTT messages. 
mqttClient.loop();

// ===================================================
  // CHECK TIME SYNCHRONIZATION
  // ===================================================

  checkTimeSynchronization();

  // ===================================================
  // Read sensors
  // ===================================================

  if (bmeOK) {

    currentTemperature = bme.readTemperature();

    currentHumidity = bme.readHumidity();
  }

  // ---------------------------------------------------
  // Soil
  // ---------------------------------------------------

  int soilRaw = analogRead(SOIL_PIN);

  currentSoilPercentage =
      map(
          soilRaw,
          SOIL_DRY,
          SOIL_WET,
          0,
          100);

  currentSoilPercentage =
      constrain(
          currentSoilPercentage,
          0,
          100);

  // ---------------------------------------------------
  // Light
  // ---------------------------------------------------

  if (lightOK) {

    currentLux = lightMeter.readLightLevel();
  }

  // ===================================================
// RGB STATUS INDICATOR
// ===================================================

updateLEDStatus();

  // =========================================
// LCD SCREEN MANAGEMENT
// =========================================

static bool previousSensorError = false;
static bool previousMQTTStatus = false;

bool currentSensorError = !bmeOK || !lightOK;
bool currentMQTTStatus = mqttClient.connected();

if (currentSensorError != previousSensorError ||
    currentMQTTStatus != previousMQTTStatus) {

  previousSensorError = currentSensorError;
  previousMQTTStatus = currentMQTTStatus;

  updateLCD();
}

if (!currentSensorError && currentMQTTStatus &&
    millis() - lastScreenChange >= SCREEN_INTERVAL) {

  lastScreenChange = millis();

  currentScreen++;

  if (currentScreen > 2) {
    currentScreen = 0;
  }

  updateLCD();
}


// ===================================================
// PUBLISH SENSOR DATA EVERY 10 SECONDS
// ===================================================

static unsigned long lastPublish = 0;

if (millis() - lastPublish >= 10000) {

  lastPublish = millis();

  // Wait until NTP time is synchronized.
  if (!timeSynchronized) {

    Serial.println(
        "Sensor publish skipped: waiting for NTP synchronization."
    );

  } else if (WiFi.status() != WL_CONNECTED) {

    Serial.println(
        "Sensor publish skipped: Wi-Fi disconnected."
    );

  } else if (!mqttClient.connected()) {

    Serial.println(
        "Sensor publish skipped: MQTT disconnected."
    );

  } else {

    String payload = "{";

    payload += "\"device_id\":\"greenpulse-01\",";

    payload += "\"timestamp\":\"";
    payload += getTimestamp();
    payload += "\",";

    payload += "\"temperature\":";
    payload += String(currentTemperature, 1);
    payload += ",";

    payload += "\"humidity\":";
    payload += String(currentHumidity, 1);
    payload += ",";

    payload += "\"soil_moisture\":";
    payload += String(currentSoilPercentage);
    payload += ",";

    payload += "\"light\":";
    payload += String(currentLux, 1);

    payload += "}";

    Serial.println();
    Serial.println("Publishing sensor data...");

    if (mqttClient.publish(
          SENSOR_TOPIC,
          payload.c_str())) {

      Serial.println("Sensor data published!");

      Serial.print("Payload: ");
      Serial.println(payload);

    } else {

      Serial.println("Sensor publish FAILED!");

    }
  }
}

}

