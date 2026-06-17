#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <uri/UriBraces.h>

#define WIFI_SSID "Arun"
#define WIFI_PASSWORD "8309396883"

WebServer server(80);

const int LED1 = 2;

bool led1State = false;

void sendHtml() {
  String response = R"(
    <!DOCTYPE html><html>
      <head>
        <title>ESP32 Web Server Demo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          html { font-family: sans-serif; text-align: center; }
          body { display: inline-flex; flex-direction: column; }
          h1 { margin-bottom: 1.2em; } 
          h2 { margin: 0; }
          div { display: grid; grid-template-columns: 1fr; grid-template-rows: auto auto; grid-auto-flow: column; grid-gap: 1em; }
          .btn { background-color: #5B5; border: none; color: #fff; padding: 0.5em 1em; font-size: 2em; text-decoration: none }
          .btn.OFF { background-color: #333; }
        </style>
      </head>
      <body>
        <h1>ESP32 Web Server</h1>
        <div>
          <h2>LED 1</h2>
          <a href="/toggle/1" class="btn LED1_TEXT">LED1_TEXT</a>
        </div>
      </body>
    </html>
  )";
  response.replace("LED1_TEXT", led1State ? "ON" : "OFF");
  server.send(200, "text/html", response);
}

void setup(void) {
  Serial.begin(115200);
  delay(1000); // Let power lines stabilize
  
  pinMode(LED1, OUTPUT);
  digitalWrite(LED1, HIGH);  

  // Reduce TX power to limit the current draw spike (Prevents Brownouts)
  WiFi.setTxPower(WIFI_POWER_11dBm); 

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi ");
  Serial.print(WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    Serial.print(".");
  }
  Serial.println(" Connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.on("/", sendHtml);
  server.on(UriBraces("/toggle/{}"), []() {
    String led = server.pathArg(0);
    Serial.print("Toggle LED #");
    Serial.println(led);
    switch (led.toInt()) {
      case 1:
        led1State = !led1State;
        digitalWrite(LED1, !led1State);  // inverted for active low
        break;
    }
    sendHtml();
  });

  server.begin();
  Serial.println("HTTP server started");
}

void loop(void) {
  server.handleClient();
  delay(10);
}