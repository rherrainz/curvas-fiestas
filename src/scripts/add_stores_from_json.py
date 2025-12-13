"""
Carga sucursales desde data/stores.json:
- Si la sucursal ya existe (por code), la omite.
- Crea Region/Zone si no existen.

Uso: cd src; python scripts/add_stores_from_json.py
"""
import os
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "retail_curves.settings")

import django  # noqa: E402

django.setup()

from core.models import Region, Zone, Store  # noqa: E402
from core.services.navidad_loader import zfill_code  # noqa: E402


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "y", "si", "sí")


def main():
    data_path = project_root / "data" / "stores.json"
    if not data_path.exists():
        print(f"[add_stores] No se encontró {data_path}")
        sys.exit(1)

    items = load_json(data_path)
    created = 0
    skipped = 0

    for row in items:
        region_name = (row.get("region") or "").strip()
        zone_name = (row.get("zona") or "").strip()
        raw_code = row.get("sucursal_id") or row.get("sucursal") or row.get("code")
        code = zfill_code(raw_code, pad=0)
        if not code:
            print(f"[warn] Código inválido en fila {row!r}, se omite.")
            skipped += 1
            continue

        is_cdr = parse_bool(row.get("CDR") or row.get("cdr"))

        region, _ = Region.objects.get_or_create(name=region_name or "SIN REGION")
        zone, _ = Zone.objects.get_or_create(region=region, name=zone_name or "SIN ZONA")

        store, created_flag = Store.objects.get_or_create(
            code=code,
            defaults={
                "name": code,  # sin nombre explícito en JSON; usamos el código
                "region": region,
                "zone": zone,
                "is_distribution_center": is_cdr,
            },
        )
        if created_flag:
            created += 1
            print(f"[add_stores] Creada sucursal {store.code} ({store.name}) [{zone}/{region}] CDR={store.is_distribution_center}")
        else:
            skipped += 1

    print(f"\n[add_stores] Finalizado. Creadas: {created}. Omitidas existentes/invalidas: {skipped}.")


if __name__ == "__main__":
    main()
