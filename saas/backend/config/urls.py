from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.catalogs.urls')),
    path('api/', include('apps.projects.urls')),
    path('api/admin/', include('apps.proxy.admin_urls')),
    path('api/chat/', include('apps.proxy.urls')),
    path('', include('apps.widgets.urls')),      # /embed, /preview, /health, /ready
]
