from django.urls import path
from .views import navidad_upload_view

urlpatterns = [
    path("upload/", navidad_upload_view, name="navidad_upload"),
]
