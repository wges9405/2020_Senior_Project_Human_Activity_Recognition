def initialize():
	global status
	global static, dynamic
	global sit, stand, lay
	global walk, up, down
	global MySQL
	global BlueSCAN
	
	status = "Disconnected"
	[static, dynamic] = [0,0]
	[sit, stand, lay] = [0,0,0]
	[walk, up, down] = [0,0,0]
	MySQL = None
	BlueSCAN = None
	
