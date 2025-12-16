from django.conf import settings
from django.shortcuts import redirect, resolve_url


class LoginRequiredMiddleware:
    """Fuerza autenticacion en todas las vistas salvo las rutas exentas."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = resolve_url(settings.LOGIN_URL)
        static_prefix = self._normalize_prefix(getattr(settings, "STATIC_URL", ""))
        media_prefix = self._normalize_prefix(getattr(settings, "MEDIA_URL", ""))

        self.exempt_prefixes = [
            p for p in (
                static_prefix,
                media_prefix,
                *getattr(settings, "LOGIN_EXEMPT_PREFIXES", []),
            )
            if p
        ]

    def __call__(self, request):
        if request.user.is_authenticated or self._is_exempt(request.path_info):
            return self.get_response(request)

        next_url = request.get_full_path()
        return redirect(f"{self.login_url}?next={next_url}")

    def _is_exempt(self, path: str) -> bool:
        path = path or "/"
        return any(path.startswith(prefix) for prefix in self.exempt_prefixes)

    def _normalize_prefix(self, prefix: str) -> str:
        if not prefix:
            return ""
        return "/" + prefix.lstrip("/")
