from django.urls import path
from .views import stock_curves_view, stock_curves_data

urlpatterns = [
    path("curves/", stock_curves_view, name="stock_curves"),
    path("curves/data/", stock_curves_data, name="stock_curves_data"),
]
