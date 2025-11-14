"""
Servicio de notificación por email para autenticación.
Soporta tanto email real (SMTP) como visualización en pantalla (desarrollo).
"""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

# Detectar si estamos en desarrollo
DEBUG_MODE = getattr(settings, 'DEBUG', True)


def send_login_email(email: str, login_link: str, expiry_minutes: int = 30) -> bool:
    """
    Envía email de login o muestra enlace en log (desarrollo).
    
    En DESARROLLO: muestra el enlace en los logs de Django para que puedas copiarlo.
    En PRODUCCIÓN: envía un email real (si SMTP está configurado).
    
    Args:
        email: Email del usuario
        login_link: URL completa del enlace de verificación
        expiry_minutes: Minutos de validez del token
    
    Returns:
        True si se envió correctamente (o se loggeó en desarrollo)
    """
    
    subject = "Tu enlace de acceso a Curvas Fiestas 2025"
    
    # Contexto para email
    context = {
        "email": email,
        "login_link": login_link,
        "expiry_minutes": expiry_minutes,
        "domain": settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
    }
    
    if DEBUG_MODE:
        # En desarrollo: loguear el enlace para que el usuario lo copie
        logger.warning("=" * 70)
        logger.warning("📧 EMAIL DE LOGIN (DESARROLLO)")
        logger.warning("=" * 70)
        logger.warning(f"Para: {email}")
        logger.warning(f"Enlace: {login_link}")
        logger.warning(f"Válido por: {expiry_minutes} minutos")
        logger.warning("=" * 70)
        logger.warning("⚠️  Copia el enlace anterior en tu navegador para acceder")
        logger.warning("=" * 70)
        return True
    else:
        # En producción: enviar email real
        try:
            # Renderizar plantilla HTML del email (opcional)
            html_message = render_to_string(
                'authentication/email_login.html',
                context
            )
        except:
            html_message = f"""
            <h1>Tu enlace de acceso</h1>
            <p>Haz clic aquí para acceder: <a href="{login_link}">{login_link}</a></p>
            <p>Este enlace expira en {expiry_minutes} minutos.</p>
            """
        
        try:
            send_mail(
                subject=subject,
                message=f"Enlace de acceso: {login_link}\nExpira en {expiry_minutes} minutos",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email enviado a {email}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar email a {email}: {str(e)}")
            return False
