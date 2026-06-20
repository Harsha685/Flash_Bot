// Define the pin connected to the photoresistor junction
const int ldrPin = A0; 

void setup() {
  // Initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

void loop() {
  // Read the input on analog pin 0:
  int ldrValue = analogRead(ldrPin);
  
  // Print the value to the Serial Monitor:
  Serial.print("Light Level: ");
  Serial.println(ldrValue);
  
  // Wait 500 milliseconds before the next reading
  delay(500); 
}