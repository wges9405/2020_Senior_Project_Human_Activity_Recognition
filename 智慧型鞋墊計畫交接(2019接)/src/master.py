import sys, signal
import threading
import Queue
import time
from datetime import datetime
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException

devices = []

start = 0
isConnected = 0
isWaiting = True

flagLeft = True
flagRight = False

left_queue = Queue.Queue(10)
right_queue = Queue.Queue(10)

processLeft = True
processRight = False

mutex = threading.Lock()
condition = threading.Condition()

syn_hello = False
syn_ack = False

syn_Left_T1 = False
syn_Left_T2 = False
syn_Right_T1 = False
syn_Right_T2 = False

UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"

LeftFoot = "HSCC_BLE_0"
RightFoot = "HSCC_BLE_1"
LeftArrived = False
RightArrived = False

tp, val, tb = sys.exc_info()

fp = open("data.log", "w")

########################################################################
## Connected with two bluetooth devices                               ##
## Sample rate for each bluetooth device is about 85~90Hz             ##
## Each packet is 20 bytes                                            ##
##     Format:                                                        ##
##         counter  ax  ay  az  gx  gy  gz  clock  redundant   "!"    ##
##             1    2   2   2   2   2   2     1        5        1     ##
########################################################################

## Handle the notifications from blue-tooth
class MyDelegate(DefaultDelegate):
    def __init__(self, params, i):
        DefaultDelegate.__init__(self)
        self.name = params
        self.i = i

        self.buffer = []

        self.queue = Queue.Queue(1)
        self.inpo_queue = Queue.Queue(500)

        self.syn = False
        self.syn_num = 0

        self.time_syn = 7
        self.t1 = 0
        self.t2 = 0
        self.carry = 0

        ## successful packet
        self.time_counter = 0
        self.counter = 0
        self.pre_counter = 0

        self.loss = False
        self.pre_data = []

        self.pre_time = 0
        self.time_carry = 0

        self.system_time = 0

    def handleNotification(self, cHandle, data):
        try:
            if not self.syn: ##IF handshaking process has not completed
                global syn_hello
                global syn_ack

                if ord(data[0]) == 1:
                    print "syn_hello"
                    syn_hello = True
                if ord(data[0]) == 3:
                    print "syn_ack"
                    syn_ack = True
                    self.syn = True

            elif(self.time_syn < 7):
                global syn_Left_T1, syn_Left_T2, syn_Right_T1, syn_Right_T2

                if(self.name == LeftFoot):
                    if(self.time_syn < 1):
                        print "syn_Left_T1"
                        self.carry = ord(data[0])
                        self.t1 = ord(data[1])
                        self.clockinfoprocessing(self.carry, self.t1)
                        syn_Left_T1 = True

                    elif(self.time_syn < 7):
                        print "syn_Left_T2"
                        self.carry = ord(data[0])
                        self.t1 = ord(data[1])
                        self.clockinfoprocessing(self.carry, self.t1)

                    if(self.time_syn == 6):
                        syn_Left_T2 = True

                    self.time_syn += 1

                else:
                    if(self.time_syn < 7):
                        print "syn_Right_T1"
                        self.carry = ord(data[0])
                        self.t1 = ord(data[1])
                        self.clockinfoprocessing(self.carry, self.t1)
                        syn_Right_T1 = True

                    elif(self.time_syn < 7):
                        print "syn_Right_T2"
                        self.carry = ord(data[0])
                        self.t1 = ord(data[1])
                        self.clockinfoprocessing(self.carry, self.t1)

                    if(self.time_syn == 6):
                        syn_Right_T2 = True

                    self.time_syn += 1
            ##Start to receive packets from peripherals
            else:
                self.parser(data)

        except:
            BTLEException.DISCONNECTED
            info = sys.exc_info()
            print self.name + " stopped"
            print info[0], ":", info[1], ":", info[2]


    def clockinfoprocessing(self, carry, ms):
        print(self.name), (carry*256+ms)


    def parser(self, data):
        global processLeft, processRight, mutex
        ## data is 20 bytes long
        for byte in data:
            if ord(byte) == 0x21:
                self.counter += 1
                ##If it is a completed packet
                if len(self.buffer) == 19:
                    self.system_time = str(datetime.now())
                    self.cur_data = self.decode(self.buffer)

                    if self.loss:
                        self.interpolation(self.pre_data, self.cur_data)
                        self.loss = False

                    mutex.acquire()
                    if (not processRight & processLeft):
                        self.write_data(self.cur_data)

                        processRight = True
                        processLeft = False

                    elif (not processLeft & processRight):
                        self.write_data(self.cur_data)

                        processLeft = True
                        processRight = False

                    mutex.release()

                    #self.check_inpo_buffer()
                    #self.buffering(self.cur_data)
                    #self.write_data(self.cur_data)
                    self.pre_data = self.cur_data
                    self.pre_counter = self.cur_data[0]
                ##Otherwise, set loss to true to trigger the interpolation process
                else:
                    self.loss = True

                self.buffer = []
            ##If the exclamation mark has not received
            else:
                self.buffer.append(ord(byte))

    def decode(self, data):
        # counter ax ay az gx gy gz ms
        tmp = []
        length = 14

        # counter
        if (data[0] > 0x21):
            data[0] -= 1
        tmp.append(data[0])

        # sensor motion
        for i in range(1, length - 1, 2):
            unsigned = (data[i] << 8) | (data[i + 1])
            signed = unsigned - 65536 if unsigned > 32767 else unsigned
            tmp.append(signed)

        # time process
        if data[length - 1] == 0x21:
            data[length - 1] -= 1
        if self.pre_time > data[length - 1]:
            self.time_carry += 1
        tmp.append(self.time_carry * 256 + data[length - 1])
        self.pre_time = data[length - 1]

        return tmp

    def buffering(self, data):
        ## according to queuing theory, if the consume speed
        ## is quicker than the produce speed, then we just
        ## need to set the buffer size to 1
        self.queue.put(data)
        if self.queue.qsize() > 0:
            self.consuming()

    def consuming(self):
        global flagLeft, flagRight, mutex, condition
        global left_queue, right_queue

        ## start critical section ##
        mutex.acquire()
        if self.name == LeftFoot:
            if True:#not flagRight & flagLeft:
                #if(right_queue.qsize() > 0):
                    #self.write_data(right_queue.get())

                ## consume the first 1 packets from the queue
                for i in range(1):
                    self.write_data(self.queue.get())

                flagLeft = False
                flagRight = True
            #else:
                #left_queue.put(self.queue.get())

        else:
            if True:#not flagLeft & flagRight:
                #if (left_queue.qsize() > 0):
                    #self.write_data(left_queue.get())

                ## consume the first 1 packets from the queue
                for i in range(1):
                    self.write_data(self.queue.get())

                flagLeft = True
                flagRight = False

            #else:
                #right_queue.put(self.queue.get())

        mutex.release()
        ## finish critical section ##

    def check_inpo_buffer(self):
        while(self.inpo_queue.qsize() > 0):
            print('----------interpolation----------')
            fp.write('----------interpolation----------\n')
            self.write_data(self.inpo_queue.get())


    def interpolation(self, x1, x2):
        x1_seq = x1[0]
        x2_seq = x2[0]

        for i in range(x1_seq + 1, x2_seq):
            self.new_data = []
            self.new_data.append(i)

            for j in range(1, 8):
                val1 = x1[j]
                val2 = x2[j]
                slope = (val2 - val1) / float(x2_seq - x1_seq)
                self.new_data.append(val1 + (i - x1_seq) * slope)

            self.inpo_queue.put(self.new_data)
            #print('----------interpolation----------')
            #fp.write('----------interpolation----------\n')
            #self.write_data(self.new_data)


    def write_data(self, data):

        ## Counter part
        print(self.name), (self.counter), (self.time_counter),
        fp.write("{}, ".format(self.system_time))
        fp.write("{}, ".format(self.name))
        fp.write("{}, ".format(self.counter))
        fp.write("{}, ".format(self.time_counter))
        self.time_counter += 1

        # Sensor motion part
        for i in range(1, 7):
            if (i > 3):
                offset = 131.0
            else:
                offset = 16384.0
            val = float(data[i]) / offset
            print("{0:.3f}".format(round(val, 3))),
            fp.write("{0:.3f}, ".format(round(val, 3)))

        # Clock info part
        for i in range(7, len(data)):
            print(data[i])
            fp.write("{0:.2f}".format(round(data[i], 2)))

        #print("\n")
        fp.write('\n')


class Process(threading.Thread):
    def __init__(self, lock, threadname):
        super(Process, self).__init__(name=threadname)

    def run(self):
        tmp = []


class BleConnect(threading.Thread):
    def __init__(self, lock, threadname, dev):
        super(BleConnect, self).__init__(name=threadname)

        self.dev = dev
        self.lock = lock

    def run(self):
        global devices, LeftArrived, RightArrived, mutex, condition

        try:
            self.lock.acquire()
            print("BleConnect:"), (threading.currentThread())
            self.p = Peripheral(self.dev.addr) ##Connect to the peripheral by its MAC address
            self.lock.release()

            i = 0
            self.p.setDelegate(MyDelegate(self.name, i)) ##Register the callback function
            service = self.p.getServiceByUUID(UUID) ##Find the desired bluetooth service by UUID
            self.ch = service.getCharacteristics() ##Find the characteristic of the desired service.
                                                   ##See Bluetooth SPEC Service Discovery Protocol for more information.
            for char in self.ch:
                if char.uuid == UUID:
                    break

            self.lock.acquire()
            self.handshaking(self.p, self.ch) ##Start handshaking protocol
            self.lock.release()

            #mutex.acquire()
            self.lock.acquire()
            condition.acquire()
            ##Time synchronization on Feet mechanism. See monthly report for more information.
            if (self.name == LeftFoot) & (not RightArrived):
                print(self.name), ("is waiting")
                LeftArrived = True
                self.lock.release()
                condition.wait() ##Let the thread to sleep
                self.ch[0].write("4")

                print(self.name), (str(datetime.now()))

            elif (self.name == RightFoot) & (not LeftArrived):
                print(self.name), ("is waiting")
                RightArrived = True
                self.lock.release()
                condition.wait() ##Let the thread to sleep
                self.ch[0].write("4")

                print(self.name), (str(datetime.now()))

            else:
                print(self.name), ("is notifying")
                condition.notify() ##Notify all sleeping threads
                self.lock.release()
                self.ch[0].write("4")

                print(self.name), (str(datetime.now()))

            condition.release()

            # the time difference between two threads
            fp.write("{}, ".format(str(datetime.now())))
            fp.write("{}, ".format(self.name))

            #---------------------------------
            ##self.time_syn_processing(self.p, self.ch)
            #---------------------------------

            receive_lock = threading.Lock()
            BleReceive(receive_lock, self.name, self.p).start() ##Start receiving process

        except:
            BTLEException.DISCONNECTED
            self.p.disconnect()
            info = sys.exc_info()
            print self.name + " stopped"
            print info[0], ":", info[1], ":", info[2]


    def time_syn_processing(self, p, ch):
        global syn_Left_T1, syn_Left_T2, syn_Right_T1, syn_Right_T2

        if(self.name == LeftFoot):
            while True:
                ch[0].write("5")
                p.waitForNotifications(5.0)
                if syn_Left_T1:
                    break

            while True:
                print "sleep for 10 secs"
                time.sleep(1)
                ch[0].write("5")
                p.waitForNotifications(5.0)
                if syn_Left_T2:
                    break
        else:
            while True:
                ch[0].write("5")
                p.waitForNotifications(5.0)
                if syn_Right_T1:
                    break

            while True:
                print "sleep for 10 secs"
                time.sleep(1)
                ch[0].write("5")
                p.waitForNotifications(5.0)
                if syn_Right_T2:
                    break


    def handshaking(self, p, ch):
        global syn_hello
        global syn_ack

        while True:
            print("Waiting for hello...")
            p.waitForNotifications(5.0)
            if syn_hello:
                ch[0].write("2")
                print("Sending hello_ack")
                break

        while True:
            print("Waiting for ACK...")
            p.waitForNotifications(5.0)
            if syn_ack:
                break
        ## There are two blue-tooth devices
        syn_hello = False
        syn_ack = False


## No need in one-to-many bluetooth transmission,
## but can be extended in other situation
class BleSend(threading.Thread):
    def __init__(self, lock, threadname, char):
        super(BleSend, self).__init__(name=threadname)
        self.char = char

    def run(self):
        global isConnected
        isRunning = True
        print "Welcome to Echo Server"

        while isRunning:
            time.sleep(10)
            if isConnected:
                try:
                    self.char.write("WelcometoEchoServer")
                    print "10secs are passed"
                except:
                    isRunning = False
                    info = sys.exc_info()
                    print self.name + " stopped"
                    print info[0], ":", info[1], ":", info[2]
            else:
                isRunning = False
                reset()


class BleReceive(threading.Thread):
    def __init__(self, lock, threadname, p):
        super(BleReceive, self).__init__(name=threadname)
        self.p = p
        self.lock = lock

    def run(self):
        print("BleReceive:"), (threading.currentThread())
        global isWaiting, mutex, flagLeft, flagRight
        i = 0
        while isWaiting:
            try:
                self.lock.acquire()
                self.p.waitForNotifications(1.0) ##If there is any received packets, trigger the callback function
                self.lock.release()
            except:
                info = sys.exc_info()
                print info[0], ":", info[1], ":", info[2]
            i += 1


class BleScan(threading.Thread):
    def __init__(self, lock, threadname):
        super(BleScan, self).__init__(name=threadname)
        self.lock = lock

    def run(self):
        global devices
        global isConnected
        connect_lock = threading.Lock()
        while True:
            print("BLEScanning..."), (threading.currentThread())
            if (isConnected < 2):
                try:
                    devicelist = Scanner(0).scan(3.0)
                    for dev in devicelist:
                        device_name = dev.getValueText(9)
                        if "HSCC_BLE_" in str(device_name): ##If desired peripherals are found
                            if dev not in devices: ##Connect to the same peripheral only once
                                devices.append(dev)
                                BleConnect(connect_lock, device_name, dev).start() ##Start connecting process
                                isConnected += 1
                except:
                    print "Scanning again"
            else:
                print "BLEScanning stopped"
                break

            time.sleep(1)


def signal_handler(signal, frame):
    print("Ctrl+z detected")
    fp.close()


def reset():
    global devices
    global start
    global isConnected
    global isWaiting
    global syn_hello
    global syn_ack

    devices = []
    start = 0
    isConnected = 0
    isWaiting = True
    syn_hello = False
    syn_ack = False

    print "Reset done"


def main():
    # Testing: write system commands directly #
    #call(["sudo bash", "-c echo 6 > /sys/kernel/debug/bluetooth/hci0/conn_min_interval"])
    #call(["sudo bash", "-c echo 7 > /sys/kernel/debug/bluetooth/hci0/conn_max_interval"])
    scan_lock = threading.Lock()
    BleScan(scan_lock, "BLEScan").start() ##Start the scanning process


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
