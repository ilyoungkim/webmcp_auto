from django.urls import path

from . import views

urlpatterns = [
    path('signup/', views.signup),
    path('login/', views.login_view),
    path('logout/', views.logout_view),
    path('password/', views.change_password),
    path('me/', views.me),
    path('csrf/', views.csrf_token),
]
