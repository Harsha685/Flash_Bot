#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <DHT.h>

// ── Pin Definitions ─────────────────────────────────────────────────────────
#define DHT_PIN          4      // GPIO4 → DHT11 data line
#define I2C_SDA_PIN      21     // ESP32 DevKit V1 default SDA
#define I2C_SCL_PIN      22     // ESP32 DevKit V1 default SCLarduino-cli lib install "Adafruit Unified Sensor"

// ── Sensor Config ───────────────────────────────────────────────────────────
#define DHT_TYPE         DHT11
#define BMP280_ADDR_PRI  0x76   // SDO → GND
#define BMP280_ADDR_SEC  0x77   // SDO → VCC (fallback)
#define SEA_LEVEL_HPA    1013.25f  // Update from local forecast for accurate altitude
#define READ_INTERVAL_MS 2000UL
#define TEMP_DELTA_WARN  5.0f   // °C — warn if sensors disagree beyond this

// ── Sensor Objects ──────────────────────────────────────────────────────────
static DHT            dht(DHT_PIN, DHT_TYPE);
static Adafruit_BMP280 bmp;

// ── Timing ──────────────────────────────────────────────────────────────────
static unsigned long lastReadMs = 0;

// ── Data Struct ─────────────────────────────────────────────────────────────
// Decouple reading from printing — lets you later log, transmit, or display
// without duplicating sensor calls.
struct WeatherData {
  float tempDHT;      // °C from DHT11
  float humidity;     // % RH
  float heatIndex;    // °C computed
  float tempBMP;      // °C from BMP280 (onboard sensor)
  float pressureHPa;  // hPa
  float altitudeM;    // metres above sea level
  bool  dhtValid;
  bool  bmpValid;
};

// ── Helper: BMP280 init with address fallback ────────────────────────────────
static bool initBMP280() {
  if (bmp.begin(BMP280_ADDR_PRI)) return true;
  // SDO pin might be pulled high — try secondary address before giving up
  if (bmp.begin(BMP280_ADDR_SEC)) {
    Serial.println(F("[WARN] BMP280 found at 0x77 (secondary address)"));
    return true;
  }
  return false;
}

// ── Read all sensors into a struct ──────────────────────────────────────────
static WeatherData readSensors() {
  WeatherData d = {};  // zero-initialise

  // DHT11 — returns NaN on wiring/timeout failures
  float hum   = dht.readHumidity();
  float tempC = dht.readTemperature();
  d.dhtValid  = !(isnan(hum) || isnan(tempC));
  if (d.dhtValid) {
    d.humidity  = hum;
    d.tempDHT   = tempC;
    d.heatIndex = dht.computeHeatIndex(tempC, hum, /*isFahrenheit=*/false);
  }

  // BMP280 — also check its outputs for NaN; sensor can misbehave mid-run
  float pres    = bmp.readPressure();
  float tempBMP = bmp.readTemperature();
  float alt     = bmp.readAltitude(SEA_LEVEL_HPA);
  d.bmpValid    = !(isnan(pres) || isnan(tempBMP) || isnan(alt));
  if (d.bmpValid) {
    d.pressureHPa = pres / 100.0f;  // Pa → hPa (explicit float division)
    d.tempBMP     = tempBMP;
    d.altitudeM   = alt;
  }

  return d;
}

// ── Print formatted weather report ──────────────────────────────────────────
static void printWeather(const WeatherData& d) {
  Serial.println(F("\n╔══ Weather Station ══════════════════╗"));

  if (d.dhtValid) {
    Serial.print(F("║ Temp  (DHT11)  : ")); Serial.print(d.tempDHT,  1); Serial.println(F(" °C"));
    Serial.print(F("║ Humidity       : ")); Serial.print(d.humidity,  1); Serial.println(F(" %"));
    Serial.print(F("║ Heat Index     : ")); Serial.print(d.heatIndex, 1); Serial.println(F(" °C"));
  } else {
    Serial.println(F("║ [ERR] DHT11 read failed — check wiring"));
  }

  Serial.println(F("║──────────────────────────────────────"));

  if (d.bmpValid) {
    Serial.print(F("║ Pressure       : ")); Serial.print(d.pressureHPa,  2); Serial.println(F(" hPa"));
    Serial.print(F("║ Altitude       : ")); Serial.print(d.altitudeM,    1); Serial.println(F(" m"));
  } else {
    Serial.println(F("║ [ERR] BMP280 read failed — check I2C"));
  }

  // Cross-validate: two temp sensors should roughly agree
  // A big delta usually means one sensor is getting heated by something nearby
  if (d.dhtValid && d.bmpValid) {
    float delta = fabsf(d.tempDHT - d.tempBMP);
    if (delta > TEMP_DELTA_WARN) {
      Serial.print(F("║ [WARN] Sensor temp delta: "));
      Serial.print(delta, 1);
      Serial.println(F(" °C — check placement/airflow"));
    }
  }

  Serial.println(F("╚══════════════════════════════════════"));
}

// ────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);  // Required on USB-CDC variants (S2, S3, etc.)

  Serial.println(F("\n[+] Weather Station starting..."));

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  dht.begin();

  if (!initBMP280()) {
    Serial.println(F("[FATAL] BMP280 not found."));
    Serial.print(F("        Sensor ID: 0x")); Serial.println(bmp.sensorID(), HEX);
    Serial.println(F("        0xFF = bad address | 0x56-0x58 = BMP280 | 0x60 = BME280"));
    Serial.println(F("        Restarting in 5 s..."));
    delay(5000);
    ESP.restart();  
  }

  bmp.setSampling(
    Adafruit_BMP280::MODE_NORMAL,
    Adafruit_BMP280::SAMPLING_X1,     // Temp: X2 is sufficient for BMP280
    Adafruit_BMP280::SAMPLING_X16,    // Pressure: max oversampling for accuracy
    Adafruit_BMP280::FILTER_X16,      // IIR filter smooths transient spikes
    Adafruit_BMP280::STANDBY_MS_500   // 500 ms between internal measurements
  );

  Serial.println(F("[+] BMP280 OK"));
  Serial.println(F("[+] DHT11 OK"));
  Serial.println(F("[+] Ready\n"));
}

  // millis() rollover-safe non-blocking interval
  // CPU is free between reads for WiFi, display, buttons, etc.
void loop() {
  printWeather(readSensors());     // what function gives you the data to print?
  
  Serial.flush();          // this one's free, just copy it
  
  esp_sleep_enable_timer_wakeup(60 * 1000000ULL);  // microseconds for 1 minute
  esp_deep_sleep_start();  // this one's free too
}
