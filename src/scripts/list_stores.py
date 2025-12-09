"""
Lista códigos de Store en la BD (muestra primeras 200)
Uso: desde src: python scripts/list_stores.py
"""
import sys
from pathlib import Path
import os

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retail_curves.settings')
import django
django.setup()

from core.models import Store

print('Total stores:', Store.objects.count())
print('Primeros 200 códigos:')
for code in Store.objects.order_by('code').values_list('code', flat=True)[:200]:
    print(repr(code))
