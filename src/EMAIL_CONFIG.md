# Configuración de Email para Autenticación

Este documento explica cómo configurar el envío de emails para el sistema de autenticación de Curvas Fiestas 2025.

## Estado Actual

- **Desarrollo**: Los enlaces se muestran en los logs de la consola Django
- **Producción**: Se envía email real (requiere configuración)

## Opciones de Configuración

### Opción 1: Gmail Personal (Recomendado para desarrollo/pruebas)

#### Pasos:

1. **Habilitar acceso de aplicaciones en tu cuenta Gmail**:
   - Ve a: https://myaccount.google.com/security
   - Busca "Acceso de aplicaciones menos seguras" o "App passwords"
   - Si tienes autenticación de dos factores habilitada:
     - Ve a: https://myaccount.google.com/apppasswords
     - Selecciona dispositivo y navegador
     - Copia la contraseña generada (16 caracteres)

2. **Configurar variables de entorno**:

```bash
# En Windows (PowerShell):
$env:EMAIL_PROVIDER = "gmail"
$env:EMAIL_HOST_USER = "tu.email@gmail.com"
$env:EMAIL_HOST_PASSWORD = "xxxx xxxx xxxx xxxx"  # 16 caracteres de Google
$env:DEFAULT_FROM_EMAIL = "tu.email@gmail.com"

# O en archivo .env (crear en la raíz del proyecto):
EMAIL_PROVIDER=gmail
EMAIL_HOST_USER=tu.email@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=tu.email@gmail.com
```

3. **En settings.py ya está configurado**:
   ```python
   EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'gmail').lower()
   EMAIL_HOST = 'smtp.gmail.com'
   EMAIL_PORT = 587
   ```

#### Características:
- ✅ Fácil de configurar
- ✅ No requiere infraestructura corporativa
- ⚠️ Usa cuenta personal (no corporativa)
- ⚠️ Las contraseñas de aplicación expiran en algunos casos

---

### Opción 2: Office 365 Corporativo (Recomendado para producción)

#### Pasos:

1. **Obtener credenciales corporativas**:
   - Usuario: `tu.usuario@laanonima.com.ar`
   - Contraseña: Tu contraseña corporativa de Office 365

2. **Configurar variables de entorno**:

```bash
# En Windows (PowerShell):
$env:EMAIL_PROVIDER = "office365"
$env:EMAIL_HOST_USER = "tu.usuario@laanonima.com.ar"
$env:EMAIL_HOST_PASSWORD = "tu.contraseña.corporativa"
$env:DEFAULT_FROM_EMAIL = "tu.usuario@laanonima.com.ar"

# O en archivo .env:
EMAIL_PROVIDER=office365
EMAIL_HOST_USER=tu.usuario@laanonima.com.ar
EMAIL_HOST_PASSWORD=tu.contraseña.corporativa
DEFAULT_FROM_EMAIL=tu.usuario@laanonima.com.ar
```

3. **En settings.py ya está configurado**:
   ```python
   EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'office365').lower()
   EMAIL_HOST = 'smtp.office365.com'
   EMAIL_PORT = 587
   ```

#### Características:
- ✅ Usa infraestructura corporativa
- ✅ Mayor seguridad y confiabilidad
- ✅ Las mails se envían desde dominio corporativo
- ⚠️ Requiere credenciales reales

---

## Testear la Configuración

Una vez configuradas las variables de entorno, reinicia Django:

```bash
python manage.py runserver
```

Luego:

1. Ve a la página de login: `http://localhost:8000/auth/login/`
2. Ingresa un email con dominio `@laanonima.com.ar`
3. En **DESARROLLO**: El enlace aparecerá en los logs de consola
4. En **PRODUCCIÓN** (DEBUG=False): Se enviará un email real

## Solucionar Problemas

### "smtplib.SMTPAuthenticationError"
- La contraseña es incorrecta o expiró
- Asegúrate de estar usando:
  - Gmail: Contraseña de aplicación (16 caracteres)
  - Office 365: Contraseña corporativa actual

### "smtplib.SMTPException: SMTP AUTH extension not supported"
- El servidor SMTP no reconoce el proveedor
- Verifica que EMAIL_PROVIDER esté configurado correctamente

### Los emails no se envían (sin error)
- DEBUG=True: Los emails se loguean en consola, no se envían realmente
- DEBUG=False: Verifica que EMAIL_BACKEND sea `smtp.EmailBackend`

## Notas Importantes

- **Nunca** guardes contraseñas en el código
- Usa variables de entorno o archivo `.env` (agrégalo a `.gitignore`)
- Para desarrollo local, es suficiente verlos en los logs
- Para producción, configura el servidor SMTP corporativo

## Variables de Entorno Disponibles

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `EMAIL_PROVIDER` | Proveedor ('gmail' o 'office365') | `office365` |
| `EMAIL_HOST_USER` | Correo o usuario SMTP | `usuario@laanonima.com.ar` |
| `EMAIL_HOST_PASSWORD` | Contraseña o App Password | `xxxx xxxx xxxx xxxx` |
| `DEFAULT_FROM_EMAIL` | Email "De" para los emails | `noreply@laanonima.com.ar` |

---

**Última actualización**: 14 de noviembre de 2025
