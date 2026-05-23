#include <Arduino.h>
#line 1 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino"
#line 1 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino"
void setup();
#line 6 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino"
void loop();
#line 1 "/home/harsha-vardhan/Desktop/Projects/FlashBot/sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino"
void setup() {
    Serial.begin(9600);
    pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
    Serial.println("blink");
    digitalWrite(LED_BUILTIN, HIGH);
    delay(1000);
    digitalWrite(LED_BUILTIN, LOW);
    delay(1000);
}
