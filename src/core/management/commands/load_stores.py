import json
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Region, Zone, Store

def str_to_bool(val):
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    if s in {"TRUE", "T", "1", "YES", "Y"}:
        return True
    if s in {"FALSE", "F", "0", "NO", "N", ""}:
        return False
    raise ValueError(f"Boolean inválido: {val!r}")

class Command(BaseCommand):
    help = "Carga regiones, zonas y sucursales (incluye CDR) desde un JSON de objetos."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            nargs="?",
            help="Ruta al archivo JSON. Si se omite, lee desde STDIN."
        )
        parser.add_argument(
            "--pad",
            type=int,
            default=0,
            help="Ancho de zero-padding para sucursal_id (ej. --pad 3 -> 035). 0 = sin padding."
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts.get("json_path")
        pad = opts.get("pad", 0)

        # Leer JSON
        try:
            if path:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.load(sys.stdin)
        except Exception as e:
            raise CommandError(f"No pude leer el JSON: {e}")

        if not isinstance(data, list):
            raise CommandError("El JSON debe ser una lista de objetos.")

        created_regions = 0
        created_zones = 0
        created_stores = 0
        updated_stores = 0

        # caches simples para evitar queries repetidas
        region_cache = {}
        zone_cache = {}

        for i, row in enumerate(data, start=1):
            try:
                region_name = str(row["region"]).strip()
                zone_name = str(row["zona"]).strip()
                code_raw = str(row["sucursal_id"]).strip()
                is_cdr = str_to_bool(row.get("CDR", "FALSE"))
            except KeyError as ke:
                raise CommandError(f"Fila {i}: falta la clave {ke!s}")
            except Exception as e:
                raise CommandError(f"Fila {i}: error de parseo: {e}")

            # padding opcional
            code = code_raw.zfill(pad) if pad and code_raw.isdigit() else code_raw

            # Region
            region = region_cache.get(region_name)
            if not region:
                region, r_created = Region.objects.get_or_create(name=region_name)
                if r_created:
                    created_regions += 1
                region_cache[region_name] = region

            # Zone (por región)
            zone_key = (region.id, zone_name)
            zone = zone_cache.get(zone_key)
            if not zone:
                zone, z_created = Zone.objects.get_or_create(region=region, name=zone_name)
                if z_created:
                    created_zones += 1
                zone_cache[zone_key] = zone

            # Store
            defaults = {
                "name": f"{'CDR' if is_cdr else 'Sucursal'} {code}",
                "region": region,
                "zone": zone,
                "is_distribution_center": is_cdr,
            }
            store, s_created = Store.objects.get_or_create(code=code, defaults=defaults)
            if s_created:
                created_stores += 1
            else:
                # actualizar si cambió algo relevante
                changed = False
                if store.region_id != region.id:
                    store.region = region; changed = True
                if store.zone_id != zone.id:
                    store.zone = zone; changed = True
                if store.is_distribution_center != is_cdr:
                    store.is_distribution_center = is_cdr; changed = True
                # si el nombre estaba vacío o genérico distinto, refrescamos
                desired_name = defaults["name"]
                if not store.name or store.name.startswith("Sucursal ") or store.name.startswith("CDR "):
                    if store.name != desired_name:
                        store.name = desired_name; changed = True
                if changed:
                    store.save(update_fields=["region", "zone", "is_distribution_center", "name"])
                    updated_stores += 1

        self.stdout.write(self.style.SUCCESS(
            f"OK: regiones creadas={created_regions}, zonas creadas={created_zones}, "
            f"sucursales creadas={created_stores}, sucursales actualizadas={updated_stores}"
        ))
