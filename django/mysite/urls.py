"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.urls import include, path
	2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt


from django.conf.urls import url  #導入url套件
from demo import views

urlpatterns = [
	path('admin/', admin.site.urls),
	path('intro/', views.intro, name='intro'),
	path('demo/', views.demo, name='demo'),
	
	path('connecting_device/', csrf_exempt(views.connecting_device), name='connecting_device'),
	path('show_progress/', csrf_exempt(views.show_progress), name='show_progress'),
	path('predict_process/', csrf_exempt(views.predict_process), name='predict_process'),
]