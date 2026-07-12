#include <Wire.h>
#include <Adafruit_BMP280.h>

// Initialize the Adafruit BMP280 sensor using I2C
Adafruit_BMP280 bmp; 

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for serial monitor to connect
  Serial.println(F("BMP280 Test Setup..."));

  // Start I2C communication on default ESP32 pins (SDA=21, SCL=22)
  // 0x76 is the standard I2C address for most cheap BMP280 modules. 
  // If it fails, try changing the address to 0x77.
  unsigned status = bmp.begin(0x76);  
  
  if (!status) {
    Serial.println(F("Could not find a valid BMP280 sensor, check wiring!"));
    Serial.print("SensorID was: 0x"); 
    Serial.println(bmp.sensorID(), HEX);
    while (1) delay(10); // Halt program if sensor is missing
  }

  /* Default settings from the datasheet for normal indoor use */
  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     /* Operating Mode. */
                  Adafruit_BMP280::SAMPLING_X2,     /* Temp. oversampling */
                  Adafruit_BMP280::SAMPLING_X16,    /* Pressure oversampling */
                  Adafruit_BMP280::FILTER_X16,      /* Filtering. */
                  Adafruit_BMP280::STANDBY_MS_500); /* Standby time. */
}

void loop() {
    // Read and print Temperature
    Serial.print(F("Temperature = "));
    Serial.print(bmp.readTemperature());
    Serial.println(" *C");

    // Read and print Barometric Pressure
    Serial.print(F("Pressure = "));
    Serial.print(bmp.readPressure() / 100.0F); // Convert Pascals to hPa
    Serial.println(" hPa");

    // Calculate approximate Altitude based on standard sea-level pressure (1013.25 hPa)
    Serial.print(F("Approx Altitude = "));
    Serial.print(bmp.readAltitude(1013.25)); 
    Serial.println(" m");

    Serial.println("------------------------------------");
    delay(2000); // Take a reading every 2 seconds
}