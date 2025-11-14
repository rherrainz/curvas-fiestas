from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from .models import LoginToken
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

ALLOWED_DOMAIN = "@laanonima.com.ar"
TOKEN_EXPIRY_MINUTES = 30  # Token válido por 30 minutos


class LoginRequestView(View):
    """
    Vista para solicitar acceso por email corporativo.
    Valida que el email sea del dominio @laanonima.com.ar y genera un token de login.
    """
    
    def get(self, request):
        """Mostrar formulario de solicitud de login"""
        if request.user.is_authenticated:
            return redirect('home')
        context = {"allowed_domain": ALLOWED_DOMAIN}
        return render(request, "authentication/login_request.html", context)

    def post(self, request):
        """Procesar solicitud de login por email"""
        email = request.POST.get("email", "").strip().lower()
        
        if not email:
            return render(request, "authentication/login_request.html", {
                "error": "Por favor ingresa tu email.",
                "allowed_domain": ALLOWED_DOMAIN
            })

        # Validar dominio corporativo
        if not email.endswith(ALLOWED_DOMAIN):
            return render(request, "authentication/login_request.html", {
                "error": f"Solo se permiten emails del dominio {ALLOWED_DOMAIN}",
                "allowed_domain": ALLOWED_DOMAIN
            })

        # Crear o reutilizar usuario
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_active": True}
        )

        # Invalidar tokens previos no usados
        LoginToken.objects.filter(email=email, used=False).update(used=True)

        # Generar nuevo token
        token = LoginToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
        
        login_token = LoginToken.objects.create(
            email=email,
            token=token,
            user=user,
            expires_at=expires_at
        )

        # Construir link de login
        login_link = request.build_absolute_uri(
            reverse('authentication:verify_token', kwargs={"token": token})
        )

        logger.info(f"Token de login generado para {email}")

        return render(request, "authentication/login_sent.html", {
            "email": email,
            "login_link": login_link,
            "expiry_minutes": TOKEN_EXPIRY_MINUTES
        })


class VerifyTokenView(View):
    """
    Vista para verificar y usar el token de login.
    Si el token es válido, autentica al usuario automáticamente.
    """
    
    def get(self, request, token):
        """Verificar token e iniciar sesión"""
        try:
            login_token = LoginToken.objects.get(token=token)
        except LoginToken.DoesNotExist:
            return render(request, "authentication/login_error.html", {
                "error": "Token inválido o no encontrado."
            })

        # Verificar validez del token
        if not login_token.is_valid():
            return render(request, "authentication/login_error.html", {
                "error": "Token expirado o ya utilizado."
            })

        # Marcar como usado y autenticar
        login_token.mark_as_used()
        login(request, login_token.user, backend='django.contrib.auth.backends.ModelBackend')

        logger.info(f"Usuario {login_token.email} autenticado exitosamente")

        return redirect('home')


class LogoutView(View):
    """Vista para cerrar sesión"""
    
    @method_decorator(login_required)
    def post(self, request):
        """Procesar logout"""
        logout(request)
        return redirect('authentication:login_request')

    @method_decorator(login_required)
    def get(self, request):
        """GET también soportado para logout simple"""
        logout(request)
        return redirect('authentication:login_request')
