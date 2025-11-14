# Autenticación por Email Corporativo

## Descripción

Sistema de autenticación sin contraseñas basado en **email corporativo** (@laanonima.com.ar). Los usuarios solicitan acceso con su email corporativo, reciben un enlace seguro por correo y pueden iniciar sesión sin necesidad de contraseña.

## Características

✅ **Sin contraseñas** - Acceso mediante tokens seguros  
✅ **Dominio restringido** - Solo emails @laanonima.com.ar  
✅ **Tokens con expiración** - Válidos por 30 minutos  
✅ **Tokens de un solo uso** - Se invalidan después de ser utilizados  
✅ **Interfaz intuitiva** - Diseño con daisyUI y TailwindCSS  
✅ **Admin panel** - Gestión de tokens en Django admin  

## Flujo de Autenticación

```
1. Usuario abre /auth/login/ e ingresa su email corporativo
   ↓
2. Sistema valida que sea del dominio @laanonima.com.ar
   ↓
3. Se genera un token único y se envía por email
   ↓
4. Usuario hace clic en el enlace del email
   ↓
5. Sistema valida el token (no expirado, no usado)
   ↓
6. Usuario es autenticado automáticamente
   ↓
7. Redirige a home y puede acceder al sitio
```

## URLs

| Ruta | Descripción |
|------|-------------|
| `/auth/login/` | Formulario para solicitar acceso |
| `/auth/verify/<token>/` | Verificar token y iniciar sesión |
| `/auth/logout/` | Cerrar sesión |

## Modelos

### LoginToken

```python
class LoginToken(models.Model):
    email           # Email corporativo del usuario
    token           # Token único y seguro
    user            # Usuario autenticado (ForeignKey)
    created_at      # Fecha de creación
    expires_at      # Fecha de expiración (30 min)
    used            # ¿Ha sido utilizado?
    used_at         # Cuándo se utilizó
```

## Configuración

### Variables en `authentication/views.py`

```python
ALLOWED_DOMAIN = "@laanonima.com.ar"        # Dominio permitido
TOKEN_EXPIRY_MINUTES = 30                    # Minutos de validez del token
```

## Uso

### Para usuarios

1. **Solicitar acceso:**
   - Ir a `/auth/login/`
   - Ingresar email corporativo (ej: juan@laanonima.com.ar)
   - Sistema envía enlace por email

2. **Iniciar sesión:**
   - Abrir email y hacer clic en el enlace
   - Sesión se abre automáticamente

3. **Cerrar sesión:**
   - Menú desplegable (avatar) → Cerrar Sesión

### Para administradores

En Django admin (`/admin/`):
- Ver todos los tokens generados
- Verificar cuáles han sido usados
- Revisar email y fechas

## Seguridad

- ✅ Tokens generados con `secrets.token_urlsafe()` (CSPRNG)
- ✅ Tokens únicos y de un solo uso
- ✅ Expiración automática en 30 minutos
- ✅ Sin almacenamiento de contraseñas
- ✅ Validación de dominio de email

## Base de datos

### Requisitos

Las migraciones ya se han ejecutado. Si necesitas re-crear las tablas:

```bash
python manage.py makemigrations authentication
python manage.py migrate
```

### Esquema

```sql
CREATE TABLE authentication_logintoken (
    id BIGINT PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    token VARCHAR(64) UNIQUE NOT NULL,
    user_id INT FOREIGN KEY,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at DATETIME NULL
);
```

## Integración con vistas existentes

Las vistas protegidas deben usar el decorador `@login_required`:

```python
from django.contrib.auth.decorators import login_required

@login_required(login_url='authentication:login_request')
def mi_vista(request):
    # Solo usuarios autenticados pueden acceder
    return render(request, 'mi_template.html')
```

O en vistas basadas en clases:

```python
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(login_required, name='dispatch')
class MiVista(View):
    def get(self, request):
        return render(request, 'mi_template.html')
```

## Próximas mejoras (opcional)

- [ ] Envío real de emails (configurar SMTP)
- [ ] Página de confirmación con vista previa del email
- [ ] Reintentos limitados antes de bloquear
- [ ] Auditoría de accesos
- [ ] Login social con Azure AD
- [ ] 2FA adicional

## Contacto

Para soporte o problemas de autenticación, contactar al equipo de sistemas.
