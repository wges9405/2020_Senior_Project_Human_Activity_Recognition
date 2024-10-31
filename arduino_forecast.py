from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException
from scipy import interpolate, signal
from keras.models import load_model
from scipy.fftpack import fft
import pandas as pd
import numpy as np

import time
import threading
import sys
import pymysql

#-----For predict data---------------------------
TYPE = { 0: 'Dynamic', 1: 'Static' }
DYNAMIC = { 0: 'WALKING', 1: 'UPSTAIRS', 2: 'DOWNSTAIRS' }
STATIC = { 0: 'STANDING/SITTING', 1: 'STANDING/SITTING', 2: 'LAYING' }
#------------------------------------------------

devices = []
isConnect = False
UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
path = "./data"



# db = pymysql.connect("127.0.0.1", "root", "hscc739", "SmartInsoles")
# cursor = db.cursor()

#-----For predict data---------------------------
class Model:
	def __init__ (self):
		self.model_type = load_model('Arduino_first_layer.h5')
		self.model_dynamic = load_model('Arduino_second_layer_dynamic.h5')
		self.model_static = load_model('Arduino_second_layer_static.h5')
	
	def predict (self, X):
		y = self.model_type.predict(X)
		type = TYPE[np.argmax(y,axis=1).max()]
		activity = ''
		accuracy = 0
		
		if type=='Dynamic':
			y = self.model_dynamic.predict(X)
			activity = DYNAMIC[np.argmax(y,axis=1).max()]
			accuracy = y[0][np.argmax(y,axis=1).max()]
			

		else: 
			y = self.model_static.predict(X)
			activity = STATIC[np.argmax(y,axis=1).max()]
			accuracy = y[0][np.argmax(y,axis=1).max()]

		
		print('Predicted activity: ', activity, 'Accuracy: ', accuracy)
		
		return activity

class Preprocess:
	def __init__ (self):
		self.FIX = [5.68290, -0.55279, -2.46397] # Arduino gyroscope 校正
		self.GRAVITY = 9.80665                   # Gravitational constant
		self.cutoff = 20                         # cutoff frequence of output
		self.freq = 50                           # input frequence
	
	def run (self, raw_acc_data, raw_gyr_data):
		acc_data = self.string_to_float(raw_acc_data, 1)
		gyr_data = self.string_to_float(raw_gyr_data, 0)
		
		total_acc = [self.filter( acc_data[0] ),
					 self.filter( acc_data[1] ),
					 self.filter( acc_data[2] )]
		body_gyr  = [self.filter( gyr_data[0] ),
					 self.filter( gyr_data[1] ),
					 self.filter( gyr_data[2] )]
		
		samples = int( len(raw_acc_data)/64 )-1
		
		data_Nn = [np.array(self.split(samples, body_gyr[0])),
				   np.array(self.split(samples, body_gyr[1])),
				   np.array(self.split(samples, body_gyr[2])),
				   np.array(self.split(samples, total_acc[0])),
				   np.array(self.split(samples, total_acc[1])),
				   np.array(self.split(samples, total_acc[2]))]
		data_Ny = self.normalize(data_Nn)
		data_Fy = self.FFT(data_Ny)
		
		X = np.transpose([data_Nn, data_Ny, data_Fy], (2,3,1,0))
		return  X
	
	def string_to_float (self, data, source):
		X = []; Y = []; Z = []
		for row in data:
			if source==1: # accelerometer
				X.append( float(row[0]) )
				Y.append( float(row[1]) )
				Z.append( float(row[2]) )
			else: 		  # gyroscope
				X.append( float(row[0]))#-self.FIX[0] )
				Y.append( float(row[1]))#-self.FIX[1] )
				Z.append( float(row[2]))#-self.FIX[2] )
		return [X,Y,Z]

	def filter (self, data): # MedianFilter + LowPowerButterWorthFilter
		b,a = signal.butter(3, 2*self.cutoff/self.freq, btype='lowpass', analog=False, output='ba')
		return signal.filtfilt(b, a, signal.medfilt(data, 3))
	
	def split (self, samples, data):
		after = []
		for index in range(samples):
			after.append( data[index*64:(index+2)*64] )
		return np.transpose(after, (0,1))
		
	def normalize (self, data):
		new = []
		for i in range(len(data)):
			normalized = np.empty(shape=data[i].shape)
			mean = np.mean(data[i], axis=1)
			std = np.std(data[i], axis=1)
			for row in range(data[i].shape[0]):
				if not std[row] == 0:
					for col in range(data[i].shape[1]):
						normalized[row][col] = (data[i][row][col] - mean[row]) / std[row]
			new.append(normalized)
		return new
	
	def FFT (self, data):
		new = []
		for i in range(len(data)):
			new.append( abs(fft(data[i]))/128 )
		return new
#------------------------------------------------

class MyDelegate(DefaultDelegate):
	def __init__(self, name):
		super().__init__()
		self.name = name
		self.buffer = []
		
		#-----For predict data---------------------------
		global PATH
		self.model = Model()
		self.preprocess = Preprocess()
		self.raw_acc_data = []
		self.raw_gyr_data = []
		self.X = None
		#------------------------------------------------
	
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
				
			#-----For predict data---------------------------
			self.raw_acc_data.append(decode_data[1:4])
			self.raw_gyr_data.append(decode_data[4:7])
			
			if len(self.raw_acc_data) >= 128:
				self.X = self.preprocess.run( np.array(self.raw_acc_data), np.array(self.raw_gyr_data) )
				
				print('----Predict--------------')
				activity = self.model.predict(self.X)
				
				self.raw_acc_data = []
				self.raw_gyr_data = []
				self.X = None
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
				deviceList = Scanner(0).scan(5.0)
				print(deviceList)
				for dev in deviceList:
					deviceName = dev.getScanData()
					if "HSCC_BLE_" in str(deviceName) and dev not in devices:
						devices.append(dev)
						BlueConnect(deviceName, dev).start()
						isConnect = True
						break
			except:
				print("Scanning again")

			time.sleep(1)

if __name__ == "__main__": 
	BlueScan("BLEScan").start()

