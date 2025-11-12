import json, sys
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Family

class Command(BaseCommand):
    help = "Carga/actualiza familias desde JSON con campos: origen, sector, familia_std, subfamilia_std."

    def add_arguments(self, parser):
        parser.add_argument("json_path", nargs="?", help="Ruta al JSON. Si se omite, lee de STDIN.")
        parser.add_argument("--deactivate-missing", action="store_true",
                            help="Marca is_active=False a lo que no esté en el archivo.")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts.get("json_path")
        try:
            data = json.load(open(path, "r", encoding="utf-8")) if path else json.load(sys.stdin)
        except Exception as e:
            raise CommandError(f"No pude leer el JSON: {e}")

        if not isinstance(data, list):
            raise CommandError("El JSON debe ser una lista.")

        required = {"origen", "sector", "familia_std", "subfamilia_std"}
        seen = set()
        created = updated = deactivated = 0

        for i, row in enumerate(data, 1):
            if not required.issubset(row):
                faltan = required - set(row)
                raise CommandError(f"Fila {i}: faltan columnas {faltan}")

            key = (row["origen"].strip(), row["sector"].strip(),
                   row["familia_std"].strip(), row["subfamilia_std"].strip())
            seen.add(key)

            obj, is_new = Family.objects.update_or_create(
                origen=key[0], sector=key[1], familia_std=key[2], subfamilia_std=key[3],
                defaults={"is_active": True},
            )
            created += int(is_new)
            updated += int(not is_new)

        if opts["deactivate_missing"]:
            for obj in Family.objects.filter(is_active=True):
                k = (obj.origen, obj.sector, obj.familia_std, obj.subfamilia_std)
                if k not in seen:
                    obj.is_active = False
                    obj.save(update_fields=["is_active"])
                    deactivated += 1

        self.stdout.write(self.style.SUCCESS(
            f"OK: created={created}, updated={updated}, deactivated={deactivated}"
        ))
