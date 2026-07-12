#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>

// Pin definitions
#define TFT_CS    5
#define TFT_RST   4
#define TFT_DC    2
#define TFT_MOSI  23
#define TFT_SCLK  18

// Initialize the display
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);

int x = 10, y = 10;
int dx = 2, dy = 2;

void setup() {
  // Use the INITR_BLACKTAB variant for most 1.8" displays
  tft.initR(INITR_BLACKTAB);
  tft.fillScreen(ST77XX_BLACK);
  tft.setRotation(1);
}

void loop() {
  // Erase previous position
  tft.fillRect(x, y, 20, 20, ST77XX_BLACK);
  
  // Update position
  x += dx;
  y += dy;
  
  // Boundary checks
  if (x <= 0 || x >= 140) dx = -dx;
  if (y <= 0 || y >= 108) dy = -dy;
  
  // Draw new position
  tft.fillRect(x, y, 20, 20, ST77XX_YELLOW);
  
  delay(20);
}