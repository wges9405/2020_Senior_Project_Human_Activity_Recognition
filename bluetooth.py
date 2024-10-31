import time
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException
import threading
import sys
import pymysql

#-----For recording data-------------------------
import os
import csv
from datetime import date
from datetime import datetime

os.chdir("./data")
filename = ""
type = ""
#------------------------------------------------

devices = []
isConnect = False
UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
path = "./data"

# db = pymysql.connect("127.0.0.1", "root", "hscc739", "SmartInsoles")
# cursor = db.cursor()

class MyDelegate(DefaultDelegate):
	def __init__(self, name):
		super().__init__()
		self.name = name
		self.buffer = []
	
	def handleNotification(self, cHandle, data):
		try:
			self.parser(data)
		except KeyboardInterrupt:
			print(self.name, " disconnect")
			self.p.disconnect()
	
	def parser(self, data):
		# counter1 counter2 counter3 ax ay az gx gy gz = (1,1,1,2,2,2,2,2,2) + (0) -> arduino padding 0
		if (len(data) == 20):
			decode_data = []
			counter = (data[0] << 16) | (data[1] << 8) | (data[2]) 
			decode_data.append(counter)
			for i in range(3, 15, 2):
				unsigned = (data[i] << 8) | (data[i+1])
				signed = unsigned - 65536 if unsigned > 32767 else unsigned 
				signed = signed / 16384.0 if i <=7 else signed / 131.0
				decode_data.append(signed)
			# sql = "INSERT INTO Sensor_Data(Counter, Ax, Ay, Az, Gx, Gy, Gz) VALUES (%d, %f, %f, %f, %f, %f, %f)" % (decode_data[0], \
			#                                     decode_data[1], decode_data[2], decode_data[3], decode_data[4], decode_data[5], decode_data[6])
			# try:
			#     cursor.execute(sql)
			#     db.commit()
			# except:
			#     db.rollback()                                
			
			print(data[0], data[1], data[2], decode_data)
			
			#-----For recording data-------------------------
			with open(filename, 'a', newline='') as csvfile:
				writer = csv.writer(csvfile)
				writer.writerow(decode_data)
			#------------------------------------------------
		
		else:
			print("Data loss")

class BleReceive(threading.Thread):
	def __init__(self, threadname, p, ch):
		super().__init__(name=threadname)
		self.p = p
		self.ch = ch
	
	def run(self):
		print("BleReceive:"), (threading.currentThread())
		while True:
			try:
				self.p.waitForNotifications(2.0)
			except:
				info = sys.exec_info()
				print(info[0], ":", info[1], ":", info[2])

class BlueConnect(threading.Thread):
	def __init__(self, threadname, dev):
		super().__init__(name=threadname)
		self.dev = dev
	
	def run(self):
		print("BlueConnect: "), (threading.currentThread())
		p = Peripheral(self.dev.addr)

		p.setDelegate(MyDelegate(self.name))
		service = p.getServiceByUUID(UUID)
		character = service.getCharacteristics()
		
		BleReceive(self.name, p, character).start() ##Start receiving process

class ScanDelegate(DefaultDelegate):
	def __init__(self):
		DefaultDelegate.__init__(self)

	def handleDiscovery(self, dev, isNewDev, isNewData):
		if isNewDev:
			print("Discovered device ", dev.addr)
		elif isNewData:
			print("Received new data from ", dev.addr)

class BlueScan(threading.Thread):
	def __init__(self, threadname):
		super().__init__(name=threadname)
	
	def run(self):
		global devices
		global isConnect
		global filename
		while not isConnect:
			print("BLEScanning..."), (threading.currentThread())
			
			try:
				# scanner = Scanner().withDelegate(ScanDelegate())
				# deviceList = scanner.scan(5.0)
				deviceList = Scanner(0).scan(5.0)
				print(deviceList)
				for dev in deviceList:
					deviceName = dev.getScanData()
					if "HSCC_BLE_" in str(deviceName) and dev not in devices:
						devices.append(dev)
						BlueConnect(deviceName, dev).start()
						isConnect = True
						
						#-----For recording data-------------------------
						filename = type+'_'+date.today().strftime("%Y-%m-%d")+'_'+datetime.now().strftime("%H-%M-%S")+".csv"
						with open(filename, 'w', newline='') as csvfile:
							writer = csv.writer(csvfile)
							#writer.writerow(["counter", "ax", "ay", "az", "gx", "gy", "gz"])
						#------------------------------------------------
						
						break
			except:
				print("Scanning again")

			time.sleep(1)

if __name__ == "__main__": 
	while(type==""):
		print("Please choose your activity:\n1) Walking\n2) Upstairs\n3) Downstairs\n4) Sitting\n5) Standing\n6) Laying\n7) Test")
		inputs = input()
		if (inputs=="1"): type = "walking"
		elif (inputs=="2"): type = "upstairs"
		elif (inputs=="3"): type = "downstairs"
		elif (inputs=="4"): type = "sitting"
		elif (inputs=="5"): type = "standing"
		elif (inputs=="6"): type = "laying"
		elif (inputs=="7"): type = "aTest"
	
	BlueScan("BLEScan").start()