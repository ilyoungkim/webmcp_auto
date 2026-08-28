from django.urls import path

from . import views

urlpatterns = [
    # 콘솔 API
    path('api/projects/<int:pk>/qna/', views.qna),
    path('api/projects/<int:pk>/widget/', views.widget_config),
    path('api/projects/<int:pk>/download/config.js', views.download_config_js),
    path('api/projects/<int:pk>/download/bundle.zip', views.download_bundle),
    # 데이터 플레인
    path('embed/<str:public_id>.js', views.embed_js),
    path('preview/<int:pk>/', views.preview_html),
    path('widget-dist/<path:path>', views.widget_asset),
    path('health/', views.health),
    path('health', views.health),
    path('api/health/', views.health),
    path('api/health', views.health),
    path('ready/', views.ready),
    path('ready', views.ready),
    path('api/ready/', views.ready),
    path('api/ready', views.ready),
]
