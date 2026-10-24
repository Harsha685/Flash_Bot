#include <Arduino.h>

#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

static unsigned long beat = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, beat % 2 ? HIGH : LOW);
  Serial.print("heartbeat ");
  Serial.println(beat++);
  delay(500);
}
