from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


# Use the custom admin site instance
from portal.admin import my_admin_site

urlpatterns = [
    path('admin/', my_admin_site.urls, name='admin_dashboard'),  # Updated to use custom admin site
    path('', include('portal.urls')),  # Routes to the portal app
    path('', include('admin_adminlte.urls'))  # Routes to the admin_adminlte app

]

# Add static and media URL patterns for development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
