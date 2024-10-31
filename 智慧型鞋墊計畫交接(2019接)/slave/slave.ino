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

unsigned long counter = 0;

unsigned long pre = 0;
unsigned long diff = 0;

int Hz = 50;

double gyroX = 0.0;
double gyroY = 0.0;
double gyroZ = 0.0;

/* Packet format:
 *  Totally 20 bytes for one packet
 *    counter  ax  ay  az  gx  gy  gz  millis  redundant "!"
 *       1     2   2   2   2   2   2     1        5       1
 */

void setup() {
    Wire.begin();
    Serial.begin(115200);
    BTSerial.begin(115200);
    
    Serial.println("Initializing arduino clock...");

    /*===========init sensor==========*/
    Serial.println("Initializing I2C devices...");
    imu.initialize();
    Serial.println("Testing device connections...");
    Serial.println(imu.testConnection() ? "MPU6050 connection successful" : "MPU6050 connection failed");
    Serial.println();

    initialization();
    /*=============clock==============*/
    delay(3000);
}

void loop() {
    #ifdef AT_MODE
        if(BTSerial.available())
        {
            char c = BTSerial.read();
            Serial.print(c);
        }
        if(Serial.available())
        {
            BTSerial.write(Serial.read());
        }
    #endif
    
    send_counter(counter);
    counter++;
    
    // Request sensor data
    // time latency: 2ms
    pre = millis();
    imu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    diff = millis()-pre;

    if (counter < 1000) {
      if(ax>32767){Serial.print((ax-65536)/16384.0,5);Serial.print(' ');}
      else        {Serial.print(ax/16384.0,5);Serial.print(' ');}
      if(ay>32767){Serial.print((ay-65536)/16384.0,5);Serial.print(' ');}
      else        {Serial.print(ay/16384.0,5);Serial.print(' ');}
      if(az>32767){Serial.print((az-65536)/16384.0,5);Serial.print(' ');}
      else        {Serial.print(az/16384.0,5);Serial.print(' ');}
      if(gx>32767){Serial.print((gx-65536)/131.0,5);Serial.print(' ');gyroX = gyroX + (gx-65536)/131.0;}
      else        {Serial.print(gx/131.0,5);Serial.print(' ');gyroX = gyroX + gx/131.0;}
      if(gy>32767){Serial.print((gy-65536)/131.0,5);Serial.print(' ');gyroY = gyroY + (gy-65536)/131.0;}
      else        {Serial.print(gy/131.0,5);Serial.print(' ');gyroY = gyroY + gy/131.0;}
      if(gz>32767){Serial.print((gz-65536)/131.0,5);Serial.print(' ');gyroZ = gyroZ + (gz-65536)/131.0;}
      else        {Serial.print(gz/131.0,5);Serial.println();gyroZ = gyroZ + gz/131.0;}
    }
    else if (counter == 1000) {
      Serial.print(gyroX/1000.0, 10);Serial.print(' ');
      Serial.print(gyroY/1000.0, 10);Serial.print(' ');
      Serial.print(gyroZ/1000.0, 10);Serial.println();
    }
    send_two_byte(ax); send_two_byte(ay); send_two_byte(az);
    send_two_byte(gx); send_two_byte(gy); send_two_byte(gz);

    //這邊應該之後補時間
    for(int i=0;i<5;i++){
        int a = 0;
        BTSerial.write(a);
    }
    
    delay(20-diff);
}

// Send counter (one byte)
void send_counter(unsigned long count){
    byte buf[4];
    buf[0] = count & 255;
    buf[1] = (count >> 8)  & 255;
    buf[2] = (count >> 16) & 255;
    buf[3] = (count >> 24) & 255;

//    Serial.print(buf[2]);
//    Serial.print(" ");
//    Serial.print(buf[1]);
//    Serial.print(" ");
//    Serial.print(buf[0]);
//    Serial.print("\n");
    
    BTSerial.write(buf[2]);
    BTSerial.write(buf[1]);
    BTSerial.write(buf[0]);
}

// Send two byte data
void send_two_byte(long int val){
    byte high, low;
    high = val >> 8 & 0xFF;
    low = val & 0xFF;

    BTSerial.write(high);
    BTSerial.write(low);
}

void initialization() {
  Serial.print("Current DLPF mode: ");Serial.println(imu.getDLPFMode());
  Serial.println("DLPF: digital low-pass filter");
  Serial.println("Disabled: 0/7, Enabled: 1~6 (higher number can remove more noise, but more delay)");
  Serial.println("Gyroscope Output Rate = 8kHz(DLPF disabled)/1kHz(DLPF enabled)");
  Serial.println("Set DLPF mode = 6");
  imu.setDLPFMode(6); // original 0
  Serial.println("reference: https://ulrichbuschbaum.wordpress.com/2015/01/18/using-the-mpu6050s-dlpf/");
  Serial.println();
  
  Serial.print("Current SMPLRT_DIV: ");Serial.println(imu.getRate());
  Serial.println("Sample rate = Gyroscope Output Rate / (1 + SMPLRT_DIV)");
  Serial.println("50Hz = 1000Hz / 20(=1+19)");
  Serial.println("Set SMPLRT_DIV = 19");
  imu.setRate(1000/Hz-1); // original 0
  Serial.println();
  Serial.print("Current Full-scale gyroscope range: ");Serial.println(imu.getFullScaleGyroRange());
  Serial.println("0/1/2/3 = +/- 250/500/1000/2000 degrees/sec");
  Serial.println("Set range = 0(+/-250 degrees/sec)");
  imu.setFullScaleAccelRange(0);
  Serial.println();
  
  Serial.print("Current Full-scale accelerometer range: ");Serial.println(imu.getFullScaleAccelRange());
  Serial.println("0/1/2/3 = +/- 2/4/8/16 g");
  Serial.println("Set range = 0(+/-2g)");
  imu.setFullScaleGyroRange(0);
  Serial.println();

  Serial.println("reference: https://www.i2cdevlib.com/docs/html/class_m_p_u6050.html#acb1fa088d43d76230106a3226f343013");
}
