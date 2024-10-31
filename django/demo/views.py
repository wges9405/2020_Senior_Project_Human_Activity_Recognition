from django.shortcuts import render      #導入render套件
from django.http import HttpResponse, JsonResponse     #導入HttpResponse套件
from datetime import datetime            #導入datatime套件，取得現在的日期時間
from django.views.decorators.csrf import csrf_exempt

import demo.globals as globals ## Parameters
#from demo.s_predict import mysql
from demo.a_predict import BlueScan

# --------------------- #
# - Inrtoduction page - #
# --------------------- #
def intro(request):
	return render(request, "intro.html")

def demo(request):
	# ---------------- #
	globals.initialize() 
	# ---------------- #
	
	connection_status = globals.status
	static_percentage = globals.static
	dynamic_percentage = globals.dynamic
	
	return render(request, "demo.html", locals())  #render(request傳遞GET或POST,模板名稱,傳遞)

# ------------- #
# - Demo page - #
# ------------- #
def connecting_device(request):
	# ----------Prediction model---------- #
	
	#globals.MySQL = mysql('Test', 'hscc739@project')
	globals.BlueSCAN = BlueScan("BLEScan")
	
	# ------------------------------------ #
	connection_status = "Connecting"
	return JsonResponse(connection_status, safe=False)
	

# --------------------- #
# - forestage control - # 前端JS訪問更新数据
# --------------------- #
def show_progress(request):
	Array = [
		str(round(globals.static*100, 2)),
		str(round(globals.dynamic*100, 2)),
		str(round(globals.sit + globals.stand, 2)),
		str(round(globals.lay, 2)),
		str(round(globals.walk, 2)),
		str(round(globals.up, 2)),
		str(round(globals.down, 2))
	]
	return JsonResponse(Array, safe=False)
	
	
# --------------------- #
# - Backstage control - # 後端實際處理程序
# --------------------- #
def predict_process(request):
	# ----------Prediction model---------- #
	
	#globals.MySQL.run()
	globals.BlueSCAN.start()
	
	# ------------------------------------ #
	return JsonResponse('Start predict', safe=False)
