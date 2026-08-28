from django.urls import path

from . import views

urlpatterns = [
    path('', views.chat),
    path('report/', views.chat_error_report),
]
