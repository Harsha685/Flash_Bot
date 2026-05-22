void setup() {
    Serial.begin(9600);
    pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        if (cmd == "PING") {
            Serial.println("PONG");
        } else if (cmd == "LED_ON") {
            digitalWrite(LED_BUILTIN, HIGH);
            Serial.println("OK");
        } else if (cmd == "LED_OFF") {
            digitalWrite(LED_BUILTIN, LOW);
            Serial.println("OK");
        } else {
            Serial.println("ERR:UNKNOWN");
        }
    }
}
