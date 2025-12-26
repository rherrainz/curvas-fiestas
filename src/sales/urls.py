from django.urls import path
from .views import (
    curves_view,
    curves_data,
    sales_by_zone_view,
    sales_by_zone_data,
    status_overview_view,
    status_overview_data,
)

app_name = "sales"

urlpatterns = [
    path("curves/", curves_view, name="sales_curves"),
    path("curves/data/", curves_data, name="sales_curves_data"),
    path("comparison/by-zone/", sales_by_zone_view, name="sales_by_zone"),
    path("comparison/by-zone/data/", sales_by_zone_data, name="sales_by_zone_data"),
    path("status/", status_overview_view, name="status_overview"),
    path("status/data/", status_overview_data, name="status_overview_data"),
]
