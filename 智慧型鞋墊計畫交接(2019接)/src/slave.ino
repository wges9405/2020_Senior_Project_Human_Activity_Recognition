#include "Wire.h"
#include "I2Cdev.h"
#include "MPU6050.h"
#include "clock.h"
#include <SoftwareSerial.h>
SoftwareSerial BTSerial(8, 9); // RX | TX

//#define AT_MODE

MPU6050 imu(0x68);

int16_t ax, ay, az;
int16_t gx, gy, gz;

uint16_t counter = 0;

Clock cl;

byte global_carry = 0;
byte global_ms = 0;

unsigned long pre = 0;
unsigned long diff = 0;

/* Packet format:
 *  Totally 20 bytes for one packet
 *    counter  ax  ay  az  gx  gy  gz  millis  redundant "!"
 *       1     2   2   2   2   2   2     1        5       1
 */

void setup() {
    Wire.begin();
    Serial.begin(115200);
    BTSerial.begin(115200);

    /*===========init sensor==========*/
    Serial.println("Initializing I2C devices...");
    imu.initialize();
    Serial.println("Testing device connections...");
    Serial.println(imu.testConnection() ? "MPU6050 connection successful" : "MPU6050 connection failed");

    /*=============handshake==========*/
    handshaking();
    /*=============clock==============*/
    Serial.println("Initializing arduino clock...");
    attachInterrupt(digitalPinToInterrupt(7), clockCounter, RISING);
    /*************************************************************
     * clockInt is our interrupt, clockCounter function is       *
     * called when invoked on a RISING clock edge                *
     *                                                           *
     *        Arduino's PWM pins: 3, 5, 6, 9, 10, 11             *
     *        Arduino micro interrupt pins: 0, 1, 2, 3, 7        *
     *                                                           *
     * pin3 is used for the sensor(SCL), so we choose PWM pin11  *
     * and attach it to interrupt pin7                           *
     *************************************************************/
    //cl.startClock(0, 0, 0);
    //time_synchronize();
    delay(3000);
    //cl.startClock(0, 0, 0);
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

    // Calculate counter (one byte)
    if(counter > 255){
        counter = 0;
    }
    send_counter(counter);
    counter++;

    // Request sensor data
    // time latency: 2ms
    pre = millis();
    imu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    diff = millis()-pre;

    //cal_clock();

    send_two_byte(ax); send_two_byte(ay); send_two_byte(az);
    send_two_byte(gx); send_two_byte(gy); send_two_byte(gz);

    BTSerial.write("0");

    for(int i=0;i<5;i++){
        BTSerial.write("0");
    }

    BTSerial.write("!");

    delay(10-diff);
}

void handshaking(){
    // Send hello message
    Serial.println("Sending hello...");
    BTSerial.write(1);

    // Receive hello message
    unsigned long timer1 = millis();
    unsigned long timer2;
    while(true){
        if(BTSerial.available()){
            char h = BTSerial.read();
            if(h == '2'){
                Serial.println("Receive hello_ack");
                break;
            }
        }
        else{
            timer2 = millis();
            if((timer2 - timer1) > 1000){
                BTSerial.write(1);
                timer1 = millis();
            }
        }
    }

    // Send ACK
    BTSerial.write(3);
    Serial.println("Sending ack");
    while(true){
        if(BTSerial.available()){
            //do nothing
            break;
        }
    }
    Serial.println("Start sending packets...");
}

void time_synchronize(){
    int packet_num = 0;
    while(packet_num < 7){
        if(BTSerial.available()){
            char c = BTSerial.read();
            if(c == '5' && packet_num != 0){
                cal_clock();
                BTSerial.write(global_carry);
                BTSerial.write(global_ms);
                packet_num++;
            }
            else if(c == '5'){
                cl.startClock(0, 0, 0);
                cal_clock();
                BTSerial.write(global_carry);
                BTSerial.write(global_ms);
                packet_num++;
            }
        }
    }
}

// Send counter (one byte)
void send_counter(int count){
    byte low; // unsigned
    low = count & 0xFF;

    // Special case when conflit appears
    if(low == 0x21){
        low = 0x22;
        counter++;
    }

    int rcounter = counter;
    if(counter > 0x21)
        rcounter--;

    /*Serial.print(counter);
    Serial.print("\t");*/

    BTSerial.write(low);
}

// Send two byte data
void send_two_byte(long int val){
    byte high, low;
    high = val >> 8 & 0xFF;
    low = val & 0xFF;
    // Special case when conflit appears
    if(high == 0x21){
        if(low >= 0x7f){
            high = 0x22;
            low = 0x00;
        }
        else{
            high = 0x20;
            low = 0xff;
        }
    }
    else if(low == 0x21){
        low = 0x22;
    }
    BTSerial.write(high);
    BTSerial.write(low);
}

void cal_clock(){
    byte ms = masterClock%256;
    byte carry = masterClock/256;

    /*if(masterClock >= 256){
        masterClock -= 256;
    }

    if(ms == 0x21)
        ms == 0x22;*/

    global_ms = ms;
    global_carry = carry;
}
