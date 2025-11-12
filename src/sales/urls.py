from django.urls import path
from .views import curves_view, curves_data

urlpatterns = [
    path("curves/", curves_view, name="sales_curves"),
    path("curves/data/", curves_data, name="sales_curves_data"),
]
