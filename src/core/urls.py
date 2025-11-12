from django.urls import path
from .views import api_zones_by_region, api_stores_by_zone, api_store_info

app_name = "core"

urlpatterns = [
    path("api/zones/", api_zones_by_region, name="zones_by_region"),
    path("api/stores/", api_stores_by_zone, name="stores_by_zone"),
    path("api/store/", api_store_info, name="store_info"),
]