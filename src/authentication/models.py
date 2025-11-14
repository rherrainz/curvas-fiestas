from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
import string

class LoginToken(models.Model):
    """
    Token de login por email corporativo.
    Generado cuando se solicita acceso con email @laanonima.com.ar
    """
    email = models.EmailField(unique=False, db_index=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'expires_at']),
            models.Index(fields=['email', 'used', 'expires_at']),
        ]

    def __str__(self):
        return f"Token para {self.email} (usado: {self.used})"

    @staticmethod
    def generate_token():
        """Genera un token seguro y único"""
        return secrets.token_urlsafe(48)

    def is_valid(self):
        """Verifica si el token es válido (no expirado y no usado)"""
        return not self.used and timezone.now() <= self.expires_at

    def mark_as_used(self):
        """Marca el token como utilizado"""
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])
