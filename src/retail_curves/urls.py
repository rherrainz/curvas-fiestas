from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import HomeView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('imports/', include('imports.urls')),
    path('sales/', include('sales.urls')),
    path("stock/", include("stock.urls")),
    path('core/', include('core.urls')),
    path('insights/', include('insights.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)