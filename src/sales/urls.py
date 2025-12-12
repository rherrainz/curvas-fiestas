from django.urls import path
from .views import curves_view, curves_data, sales_by_zone_view, sales_by_zone_data

app_name = "sales"

urlpatterns = [
    path("curves/", curves_view, name="sales_curves"),
    path("curves/data/", curves_data, name="sales_curves_data"),
    path("comparison/by-zone/", sales_by_zone_view, name="sales_by_zone"),
    path("comparison/by-zone/data/", sales_by_zone_data, name="sales_by_zone_data"),
]
