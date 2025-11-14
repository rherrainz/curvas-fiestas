from django.urls import path
from .views import LoginRequestView, VerifyTokenView, LogoutView

app_name = 'authentication'

urlpatterns = [
    path('login/', LoginRequestView.as_view(), name='login_request'),
    path('verify/<str:token>/', VerifyTokenView.as_view(), name='verify_token'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
