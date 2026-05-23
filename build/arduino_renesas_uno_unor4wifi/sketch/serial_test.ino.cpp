#include <Arduino.h>
#line 1 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/serial_test/serial_test.ino"
#line 1 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/serial_test/serial_test.ino"
void setup();
#line 6 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/serial_test/serial_test.ino"
void loop();
#line 1 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/serial_test/serial_test.ino"
void setup() {
    Serial.begin(9600);
    pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "PING") Serial.println("PONG");
        if (cmd == "LED_ON") {
            digitalWrite(LED_BUILTIN, HIGH);
            Serial.println("OK");
        }
        if (cmd == "LED_OFF") {
            digitalWrite(LED_BUILTIN, LOW);
            Serial.println("OK");
        }
    }
}

