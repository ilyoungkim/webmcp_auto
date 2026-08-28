from django.urls import path

from . import views

urlpatterns = [
    path('projects/', views.projects),
    path('projects/sitemap-urls/', views.sitemap_urls),
    path('projects/<int:pk>/', views.project_detail),
    path('projects/<int:pk>/status/', views.project_status),
    path('projects/<int:pk>/sitemap-urls/', views.project_sitemap_urls),
    path('projects/<int:pk>/rerun/', views.project_rerun),
    path('projects/<int:pk>/menus/', views.project_menus),
    path('projects/<int:pk>/menus/regenerate/', views.project_menus_regenerate),
    path('projects/<int:pk>/origins/', views.project_origins),
    path('projects/<int:pk>/origins/<int:origin_id>/', views.project_origins),
    path('projects/<int:pk>/support/', views.project_support),
]
