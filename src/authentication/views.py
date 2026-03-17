from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from .models import LoginToken
from .email_service import send_login_email
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

ALLOWED_DOMAIN = "@laanonima.com.ar"
TOKEN_EXPIRY_MINUTES = 30  # Token válido por 30 minutos


def _get_safe_next_url(request, candidate: str) -> str:
    if not candidate:
        return ""

    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


class LoginRequestView(View):
    """
    Vista para solicitar acceso por email corporativo.
    Valida que el email sea del dominio @laanonima.com.ar y genera un token de login.
    """
    
    def get(self, request):
        """Mostrar formulario de solicitud de login"""
        if request.user.is_authenticated:
            return redirect('home')
        context = {
            "allowed_domain": ALLOWED_DOMAIN,
            "next_url": _get_safe_next_url(request, request.GET.get("next", "")),
        }
        return render(request, "authentication/login_request.html", context)

    def post(self, request):
        """Procesar solicitud de login por email"""
        email = request.POST.get("email", "").strip().lower()
        next_url = _get_safe_next_url(request, request.POST.get("next", ""))
        
        if not email:
            return render(request, "authentication/login_request.html", {
                "error": "Por favor ingresa tu email.",
                "allowed_domain": ALLOWED_DOMAIN,
                "next_url": next_url,
            })

        # Validar dominio corporativo
        if not email.endswith(ALLOWED_DOMAIN):
            return render(request, "authentication/login_request.html", {
                "error": f"Solo se permiten emails del dominio {ALLOWED_DOMAIN}",
                "allowed_domain": ALLOWED_DOMAIN,
                "next_url": next_url,
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
        login_path = reverse('authentication:verify_token', kwargs={"token": token})
        if next_url:
            login_path = f"{login_path}?next={next_url}"
        login_link = request.build_absolute_uri(login_path)

        # Enviar email (o log en desarrollo)
        send_login_email(email, login_link, TOKEN_EXPIRY_MINUTES)

        logger.info(f"Token de login generado para {email}")

        return render(request, "authentication/login_sent.html", {
            "email": email,
            "login_link": login_link,
            "expiry_minutes": TOKEN_EXPIRY_MINUTES,
            "debug": settings.DEBUG
        })


class VerifyTokenView(View):
    """
    Vista para verificar y usar el token de login.
    Si el token es válido, autentica al usuario automáticamente.
    """
    
    def get(self, request, token):
        """Verificar token e iniciar sesión"""
        next_url = _get_safe_next_url(request, request.GET.get("next", ""))
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

        if next_url:
            return redirect(next_url)
        return redirect(settings.LOGIN_REDIRECT_URL)


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
