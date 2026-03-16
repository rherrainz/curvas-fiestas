# Curvas Retail

Aplicación Django para analizar ventas y stock de campaña de Navidad por región, zona, sucursal y familia de producto. La app permite cargar archivos Excel operativos, consolidarlos en base de datos y visualizar curvas comparativas e indicadores de situación.

## Qué hace la app

La aplicación trabaja sobre una jerarquía comercial:

- `Region`
- `Zone`
- `Store`
- `Family`

Con esa estructura registra dos tipos de datos diarios:

- `SalesRecord`: unidades vendidas por sucursal, familia y fecha.
- `StockRecord`: stock por sucursal, familia y fecha.

El foco funcional está puesto en el período navideño, usando comparaciones entre años y cortes de fecha dentro de la campaña.

## Módulos principales

### `authentication`

Implementa login por link mágico enviado por email corporativo `@laanonima.com.ar`.

- Solicita acceso desde `/auth/login/`.
- Genera un token temporal.
- Envía un link de acceso por email.
- Exige autenticación para casi toda la aplicación.

### `imports`

Permite subir un Excel de Navidad desde `/imports/upload/`.

El importador:

- detecta automáticamente la fila de encabezados;
- valida columnas requeridas;
- procesa el archivo en chunks;
- normaliza fechas, códigos de sucursal y valores numéricos;
- crea o actualiza registros de ventas y stock;
- ignora ventas para centros de distribución;
- puede validar estrictamente región y zona contra el maestro.

Columnas esperadas en el Excel:

- `Dia`
- `Region`
- `Zona`
- `Sucursal`
- `SubFamilia`
- `Unidades Stock Final`
- `Unidades Vendidas`

### `sales`

Expone vistas para analizar ventas en campaña:

- `/sales/curves/`: curvas acumuladas por año para el período 1/octubre a 31/diciembre.
- `/sales/comparison/by-zone/`: comparación de ventas acumuladas por sucursal dentro de una zona.
- `/sales/status/`: matriz de variación 2025 vs 2024 por familia y zona o sucursal.

Características:

- filtros por región, zona, sucursal y familia;
- series comparativas entre hasta 3 años;
- coherencia automática entre sucursal, zona y región;
- exclusión de centros de distribución en ventas.

### `stock`

Expone `/stock/curves/` para comparar stock diario entre campañas.

Permite filtrar por:

- región;
- zona;
- sucursal;
- familia;
- origen del stock: todas las ubicaciones, tiendas o CDR.

### `insights`

Expone `/insights/overview/`, una vista de situación consolidada por familia.

Métricas principales:

- UV actuales acumuladas;
- stock actual;
- stock + UV actuales;
- UV totales del año anterior;
- ratio stock+venta actual vs año anterior;
- ratio UV actual vs año anterior.

La fecha de corte se ajusta al último día con datos disponibles del año pivot.

### `core`

Contiene maestros y APIs auxiliares para filtros dependientes:

- zonas por región;
- sucursales por zona;
- datos de una sucursal.

## Pantalla de inicio

La home enlaza a tres vistas principales:

- Curvas de Ventas
- Curvas de Stock
- Situación Zona/Sucursal

## Stack técnico

- Python
- Django 5
- SQLite por defecto en local
- PostgreSQL vía `DATABASE_URL` en despliegue
- Pandas + OpenPyXL para importación Excel
- Tailwind para estilos
- WhiteNoise para estáticos
- Gunicorn para producción

## Variables de entorno

En `src/.env.example` hay un ejemplo mínimo. Variables relevantes:

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `DATABASE_URL`
- `EMAIL_PROVIDER`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

Notas:

- si no hay `DATABASE_URL`, usa SQLite local;
- en desarrollo el backend de email escribe en consola;
- en producción usa SMTP;
- el dominio permitido para login es `@laanonima.com.ar`.

## Cómo levantar el proyecto

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables

Crear `src/.env` a partir de `src/.env.example`.

### 3. Migrar base de datos

```bash
cd src
python manage.py migrate
```

### 4. Cargar maestros base

El proyecto incluye comandos para cargar familias y sucursales:

```bash
python manage.py load_families
python manage.py load_stores
```

También hay datos de apoyo en:

- `src/data/families.json`
- `src/data/stores.json`

### 5. Ejecutar servidor

```bash
python manage.py runserver
```

## Flujo operativo típico

1. Cargar maestros de regiones, zonas, sucursales y familias.
2. Iniciar sesión con email corporativo.
3. Subir archivo Excel desde `/imports/upload/`.
4. Revisar curvas de ventas y stock.
5. Analizar situación consolidada desde insights y status.

## Estructura del proyecto

```text
src/
  authentication/   Login por email
  core/             Maestros y APIs auxiliares
  imports/          Carga de archivos Excel
  insights/         Indicadores consolidados
  retail_curves/    Configuración Django
  sales/            Analítica de ventas
  stock/            Analítica de stock
  theme/            Templates y assets
```

## Despliegue

El repositorio incluye `Procfile` para correr con Gunicorn:

```text
web: cd src && gunicorn retail_curves.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300
```

## Observaciones funcionales

- La campaña navideña se analiza sobre el rango 1 de octubre a 31 de diciembre.
- Las ventas se acumulan en curvas; el stock se muestra como valor diario.
- Los centros de distribución participan en stock, pero no en ventas.
- Si se filtra por sucursal, la app fuerza la región y zona correspondientes para mantener coherencia.
