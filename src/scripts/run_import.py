"""
Script para ejecutar la importación completa usando `process_navidad_file`.

Uso:
  cd src
  python scripts/run_import.py "C:\ruta\a\archivo.xlsx" [--sheet "Hoja"] [--pad 0] [--strict-area] [--backup] [--yes]

Opciones:
  --backup   : si encuentra `db.sqlite3` la copia a `db.sqlite3.YYYYMMDD_HHMMSS.bak` antes de importar
  --yes      : no pedir confirmación interactiva (útil en CI)

El script muestra progreso (los prints de `process_navidad_file`) y al final imprime el resumen.
"""
import sys
from pathlib import Path
import argparse
import os
import shutil
from datetime import datetime


def ensure_project_path():
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def backup_sqlite_if_requested(do_backup: bool):
    if not do_backup:
        return None
    db_path = Path(__file__).resolve().parent.parent / 'db.sqlite3'
    if not db_path.exists():
        print('[run_import] No se encontró db.sqlite3 para respaldar.')
        return None
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = db_path.with_name(f"db.sqlite3.{stamp}.bak")
    shutil.copy2(db_path, target)
    print(f"[run_import] Backup creado: {target}")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Ruta al archivo xlsx/csv')
    parser.add_argument('--sheet', default=None, help='Hoja (nombre o índice)')
    parser.add_argument('--pad', type=int, default=0, help='Zero-padding (0=sin padding)')
    parser.add_argument('--strict-area', action='store_true', help='Validar region/zona contra maestro')
    parser.add_argument('--backup', action='store_true', help='Hacer backup de db.sqlite3 antes de importar')
    parser.add_argument('--yes', action='store_true', help='No pedir confirmación')
    args = parser.parse_args()

    p = Path(args.file)
    if not p.exists():
        print('Archivo no encontrado:', p)
        sys.exit(1)

    ensure_project_path()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retail_curves.settings')
    try:
        import django
        django.setup()
    except Exception as e:
        print('Error iniciando Django:', e)
        sys.exit(1)

    from core.services.navidad_loader import process_navidad_file

    print('\nResumen antes de importar:')
    try:
        from core.models import Store, Family
        print('Stores en DB:', Store.objects.count())
        print('Families en DB:', Family.objects.count())
    except Exception:
        pass

    if not args.yes:
        ans = input(f"Confirma ejecutar importación sobre '{p.name}' contra la BD actual? [y/N]: ").strip().lower()
        if ans not in ('y', 'yes'):
            print('Cancelado por el usuario.')
            sys.exit(0)

    if args.backup:
        backup_sqlite_if_requested(True)

    print(f"[run_import] Iniciando importación: {p} sheet={args.sheet} pad={args.pad} strict_area={args.strict_area}\n")
    try:
        summary = process_navidad_file(p, sheet=args.sheet, pad=args.pad, strict_area=args.strict_area)
        print('\nImportación completada. Resumen:')
        for k, v in summary.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print('Error durante la importación:', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
