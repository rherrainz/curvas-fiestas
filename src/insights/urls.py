from django.urls import path
from .views import overview_view, overview_data

app_name = "insights"
urlpatterns = [
    path("overview/", overview_view, name="overview"),
    path("overview/data/", overview_data, name="overview_data"),
]
