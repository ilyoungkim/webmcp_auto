from django.urls import path

from . import views

urlpatterns = [
    path('domain-types/', views.domain_types),
    path('silo-info/', views.silo_info),
]
