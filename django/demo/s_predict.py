from keras.models import load_model
from scipy import interpolate, signal
from scipy.fftpack import fft
import pandas as pd
import numpy as np
import MySQLdb
import demo.globals as globals
import os


TYPE = { 0: 'Dynamic', 1: 'Static' }
DYNAMIC = { 0: 'WALKING', 1: 'UPSTAIRS', 2: 'DOWNSTAIRS' }
STATIC = { 0: 'SITTING/LAYING', 1: 'STANDING', 2: 'SITTING/LAYING' }

User = 'Test'
PassWD = 'hscc739@project'

class Model:
	def __init__ (self):
		self.model_type = load_model('./demo/Result/Smartphone_first_layer.h5')
		self.model_dynamic = load_model('./demo/Result/Smartphone_second_layer_dynamic.h5')
		self.model_static = load_model('./demo/Result/Smartphone_second_layer_static.h5')
	
	def predict (self, X):
		[globals.dynamic, globals.static] = [0,0]
		[globals.sit, globals.stand, globals.lay] = [0,0,0]
		[globals.walk, globals.up, globals.down] = [0,0,0]
		type = None
		activity = None
		
		y = self.model_type.predict(X)
		[globals.dynamic, globals.static] = y[0]
		type = TYPE[np.argmax(y,axis=1).max()]

		if type=='Dynamic':
			y = self.model_dynamic.predict(X)
			[globals.walk, globals.up, globals.down] = y[0]
			activity = DYNAMIC[np.argmax(y,axis=1).max()]

		else: 
			y = self.model_static.predict(X)
			[globals.sit, globals.stand, globals.lay] = y[0]
			activity = STATIC[np.argmax(y,axis=1).max()]
		
		#print(globals.dynamic, globals.static)
		#print(globals.walk, globals.up, globals.down)
		#print(globals.sit, globals.stand, globals.lay)
		#print(type, activity)

class Preprocess:
	def __init__ (self):
		self.FIX = [-5.83031, 0.57800, 2.52145]  # Arduino gyroscope 校正
		self.GRAVITY = 9.80665                   # Gravitational constant
		self.cutoff = 20                         # cutoff frequence of output
		self.freq = 50                           # input frequence
	
	def run (self, raw_acc_data, raw_gyr_data):
		raw_acc_data, acc_timestamp = self.extraction(raw_acc_data)
		raw_gyr_data, gyr_timestamp = self.extraction(raw_gyr_data)

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
		
		return  X, acc_timestamp, gyr_timestamp
	
	def extraction (self, data):
		data, timestamp = np.hsplit( np.delete(data, [0,5,6], axis=1) ,[3])
		timestamp = timestamp[-1][0]
		return data, timestamp
	
	def string_to_float (self, data, source):
		X = []; Y = []; Z = []
		for row in data:
			if source==1: # accelerometer
				X.append( float(row[0])/self.GRAVITY )
				Y.append( float(row[1])/self.GRAVITY )
				Z.append( float(row[2])/self.GRAVITY )
			else: 		  # gyroscope
				X.append( float(row[0]) )
				Y.append( float(row[1]) )
				Z.append( float(row[2]) )
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
		return abs(fft(data))/128

class mysql:
	def __init__ (self, user, passwd):
		self.model = Model()
		self.preprocess = Preprocess()
		self.conn = MySQLdb.connect(
						host = '140.114.89.66',
						db = 'smart_insole',
						user = user,
						passwd = passwd,
						port = 3306
						)
		self.cursor = self.conn.cursor()
		
		self.ready = False
		self.start = False
		self.done = False
		self.raw_acc_data = None
		self.raw_gyr_data = None
		self.X = None
		self.acc_timestamp = None
		self.gyr_timestamp = None
		
		self.cursor.execute("SELECT VERSION()") 
		print("Database version : %s \n" % self.cursor.fetchone())
		
		globals.status = 'Connecting'
	
	def run (self):
		print("Start")
		while not self.done:
			while not self.ready: self.Ready()
			if not self.done:
				self.Read()
				self.Preprocess()
				self.Predict()
				self.Clear()
		self.End()
	
	def Ready (self):
		self.cursor.execute("select count(*) from accelerometer")
		acc_rows = int(self.cursor.fetchall()[0][0])
		self.cursor.execute("select count(*) from gyroscope")
		gyr_rows = int(self.cursor.fetchall()[0][0])
		
		if acc_rows>128 and gyr_rows>128:
			self.ready = True
			self.start = True
		#else: 
		#	if self.start:
		#		self.ready = True
		#		self.done = True
		#		print("Done.\n")
	
	def Read (self):
		self.cursor.execute("select * from accelerometer")
		self.raw_acc_data = np.asarray(self.cursor.fetchmany(128))
		self.cursor.execute("select * from gyroscope")
		self.raw_gyr_data = np.asarray(self.cursor.fetchmany(128))
	
	def Preprocess (self):
		self.X, self.acc_timestamp, self.gyr_timestamp = self.preprocess.run(self.raw_acc_data, self.raw_gyr_data)
	
	def Predict (self):
		#print('----Predict--------------')
		#activity = self.model.predict(self.X)
		#print('Predicted activity: ', activity)
		#print('\n')
		
		self.model.predict(self.X)
	
	def Clear (self):
		self.Delete()
		
		self.ready = False
		self.acc_timestamp = None
		self.gyr_timestamp = None
		self.X = None
		self.raw_gyr_data = None
		self.raw_acc_data = None
	
	def Delete (self):
		self.cursor.execute("delete from accelerometer where timestamp <= "+self.acc_timestamp)
		self.cursor.execute("delete from gyroscope where timestamp <= "+self.gyr_timestamp)
	
	def End (self):
		self.cursor.execute("select * from accelerometer")
		self.acc_timestamp = str(self.cursor.fetchall()[-1][4])
		self.cursor.execute("select * from gyroscope")
		self.gyr_timestamp = str(self.cursor.fetchall()[-1][4])
		self.Delete()
	
	def Close(self):
		self.run.close()


#if __name__ == "__main__": 
#	MySQL = mysql(User, PassWD)
#	MySQL.run()
