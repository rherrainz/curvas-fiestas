# Guía de Pruebas - Autenticación por Email

## ¿Qué hace el sistema?

- **Login seguro por email** sin contraseñas
- **Solo permite** emails del dominio `@laanonima.com.ar`
- **Tokens únicos** válidos por 30 minutos
- **Tokens de un solo uso** (no puedes reutilizar un link)

## Cómo Probar en Desarrollo

### 1. Inicia el servidor Django

```bash
cd src
python manage.py runserver
```

### 2. Accede al formulario de login

Abre tu navegador y ve a:
```
http://localhost:8000/auth/login/
```

### 3. Prueba con un email válido

Ingresa un email corporativo:
```
juan@laanonima.com.ar
```

### 4. Busca el enlace en los logs

En la consola donde está corriendo Django, verás algo como:

```
======================================================================
📧 EMAIL DE LOGIN (DESARROLLO)
======================================================================
Para: juan@laanonima.com.ar
Enlace: http://localhost:8000/auth/verify/ABC123XYZ...
Válido por: 30 minutos
======================================================================
⚠️  Copia el enlace anterior en tu navegador para acceder
======================================================================
```

### 5. Opción A: Copia el enlace manualmente

Copia el enlace completo de los logs y pégalo en la barra de direcciones.

### 5. Opción B: Haz clic en el botón (Modo Desarrollo)

En la página `login_sent.html` verás un botón "Acceder ahora (desarrollo)" que hace clic automáticamente en el enlace.

## Casos de Prueba

### ✅ Caso 1: Login exitoso

1. Ingresa: `usuario1@laanonima.com.ar`
2. Copia el enlace de los logs
3. Accede al enlace
4. ✓ Deberías ser redirigido a home y estar autenticado

**Verificación:** Verás tu email en la navbar (parte superior derecha)

---

### ❌ Caso 2: Email incorrecto (dominio inválido)

1. Intenta con: `usuario@gmail.com`
2. ✓ Verás error: "Solo se permiten emails del dominio @laanonima.com.ar"

---

### ❌ Caso 3: Token expirado

1. Ingresa email válido y obtén el enlace
2. Espera 30+ minutos (o edita directamente en BD y cambia `expires_at`)
3. Intenta acceder al enlace
4. ✓ Verás error: "Token expirado o ya utilizado"

---

### ❌ Caso 4: Reutilizar token

1. Ingresa email y obtén enlace
2. Haz clic en el enlace → Autenticado ✓
3. Haz logout
4. Intenta usar el MISMO enlace nuevamente
5. ✓ Verás error: "Token expirado o ya utilizado"

---

### ✅ Caso 5: Multiple logins en paralelo

1. Usuario A: solicita acceso → obtiene enlace A
2. Usuario B: solicita acceso → obtiene enlace B
3. Usuario A: hace clic en enlace A → Autenticado
4. Usuario B: hace clic en enlace B → Autenticado
5. ✓ Ambos acceden sin problemas

---

## Verificaciones en Django Admin

Ve a: `http://localhost:8000/admin/`

### Tabla: Authentication > Login Tokens

Verás todos los tokens generados:

| Email | Generado | Expira | ¿Usado? | Fecha Uso |
|-------|----------|--------|---------|-----------|
| juan@laanonima.com.ar | 14:30:25 | 15:00:25 | Sí | 14:31:10 |
| maria@laanonima.com.ar | 14:32:10 | 15:02:10 | No | — |

### Filtros útiles:
- **Filtrar por estado:** "Usado" o "No usado"
- **Buscar por email**

---

## Pruebas Avanzadas (SQL)

### Ver tokens activos (no expirados)

```sql
SELECT email, token, created_at, expires_at 
FROM authentication_logintoken 
WHERE expires_at > NOW() AND used = 0
ORDER BY created_at DESC;
```

### Limpiar tokens expirados

```sql
DELETE FROM authentication_logintoken 
WHERE expires_at < NOW();
```

---

## Configuración de Producción

### Paso 1: Configurar SMTP (Gmail example)

En `settings.py` (o variables de entorno):

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu-correo@gmail.com'
EMAIL_HOST_PASSWORD = 'tu-app-password'  # NO tu contraseña normal
DEFAULT_FROM_EMAIL = 'noreply@laanonima.com.ar'
```

### Paso 2: Generar App Password (Gmail)

1. Activa 2FA en tu cuenta Google
2. Ve a: https://myaccount.google.com/apppasswords
3. Crea un "App Password" para Django
4. Usa ese código en `EMAIL_HOST_PASSWORD`

### Paso 3: Desplegar con DEBUG=False

En producción:
```python
DEBUG = False
ALLOWED_HOSTS = ['tu-dominio.com', 'www.tu-dominio.com']
```

---

## Troubleshooting

### Problema: "No veo el enlace en los logs"

**Solución:** 
- Asegúrate de que `DEBUG = True` en `settings.py`
- Mira la consola completa (podría estar arriba en los logs)

### Problema: "El enlace no funciona"

**Causas posibles:**
1. Token expiró (30 minutos)
2. Ya fue utilizado
3. La URL está incorrecta (cópiala bien)

**Solución:** Solicita un nuevo enlace

### Problema: "Error al acceder - Token inválido"

**Solución:**
- Asegúrate de usar email `@laanonima.com.ar`
- Copia el enlace correcto de los logs

---

## Script de Prueba Rápida (opcional)

Si quieres automatizar pruebas:

```python
# test_auth.py (en el directorio src/)
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retail_curves.settings')
django.setup()

from authentication.models import LoginToken
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Crear token de prueba
user = User.objects.create_user(
    username='test@laanonima.com.ar',
    email='test@laanonima.com.ar'
)

token = LoginToken.objects.create(
    email='test@laanonima.com.ar',
    token='test-token-12345',
    user=user,
    expires_at=timezone.now() + timedelta(hours=1)
)

print(f"✓ Token creado: {token.token}")
print(f"✓ Válido: {token.is_valid()}")
```

Ejecuta con:
```bash
python test_auth.py
```

---

## Contacto

¿Problemas? Revisa los logs o contacta al equipo de desarrollo.
