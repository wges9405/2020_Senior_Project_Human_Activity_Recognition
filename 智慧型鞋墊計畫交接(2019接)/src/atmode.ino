#include "Wire.h"
#include <SoftwareSerial.h>
SoftwareSerial BTSerial(8, 9); // RX | TX

#define AT_MODE

void setup() {
    Wire.begin();
    Serial.begin(115200);
    BTSerial.begin(115200);
}

void loop() {
    #ifdef AT_MODE
        if(BTSerial.available()){
            char c = BTSerial.read();
            Serial.print(c);
        }
        if(Serial.available()){
            BTSerial.write(Serial.read());
        }
    #endif
}
