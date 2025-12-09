# Test Scripts

Scripts de prueba para validar funcionalidades del navidad loader y normalización de datos.

## Contenido

- **test_zfill_local.py**: Prueba de la función `zfill_code` con lógica local (sin dependencias de Django)
- **test_zfill.py**: Prueba de la función `zfill_code` importada desde `navidad_loader`
- **test_navidad_norm.py**: Validación de normalización de códigos de sucursal (lstrip de ceros)

## Ejecución

```bash
# Desde src/
python scripts/test/test_zfill.py
python scripts/test/test_zfill_local.py
python scripts/test/test_navidad_norm.py
```
