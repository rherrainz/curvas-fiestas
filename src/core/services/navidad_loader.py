from pathlib import Path
from datetime import date
import pandas as pd
from openpyxl import load_workbook
from django.db import transaction
from core.models import Store, Family
from sales.models import SalesRecord
from stock.models import StockRecord

REQUIRED_COLS = [
    "Dia", "Region", "Zona", "Sucursal",
    "SubFamilia", "Unidades Stock Final", "Unidades Vendidas"
]

def parse_date(val):
    import pandas as pd
    from datetime import date, datetime

    if val is None:
        return None
    # Si ya viene como Timestamp/datetime/date -> devolvémos date
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if s == "":
        return None

    # 1) intento robusto con parse genérico (soporta "2023-10-01 00:00:00" y "01/10/2023")
    try:
        return pd.to_datetime(s, dayfirst=True, errors="raise").date()
    except Exception:
        pass

    # 2) Si viniera como número serial de Excel (poco probable con openpyxl, pero por las dudas)
    try:
        # Excel serial date (Windows): origin '1899-12-30'
        return pd.to_datetime(float(s), unit="D", origin="1899-12-30").date()
    except Exception:
        return None

def parse_number(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(" ", "")
    if s == "":
        return None
    # normalizar separadores , .
    if "," in s and "." in s:
        last_comma, last_dot = s.rfind(","), s.rfind(".")
        s = s.replace(".", "").replace(",", ".") if last_comma > last_dot else s.replace(",", "")
    else:
        if "," in s:  # solo coma -> decimal con coma
            s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def zfill_code(raw, pad):
    # Normaliza 54.0 -> "54", " 054 " -> "054"
    s = str(raw).strip()
    # ¿es numérico? (soporta "54", "54.0", 54, 54.0)
    try:
        num = float(s)
        if num.is_integer():
            s = str(int(num))
    except Exception:
        # si no es número, queda como está
        pass
    return s.zfill(pad) if (pad and s.isdigit()) else s

def _detect_header_row(df_no_header, max_scan=30):
    """
    Recorre las primeras 'max_scan' filas buscando la fila que contenga
    la mayor cantidad de columnas requeridas (usando aliases).
    Devuelve (row_idx, columns_canonicas) o (None, None) si no encuentra.
    """
    def norm(s):
        s = "" if s is None else str(s)
        return " ".join(s.replace("\n", " ").strip().lower().split())

    REQUIRED = [
        "Dia", "Region", "Zona", "Sucursal",
        "SubFamilia", "Unidades Stock Final", "Unidades Vendidas"
    ]
    ALIASES = {
        "día": "Dia", "dia": "Dia", "fecha": "Dia",
        "region": "Region", "región": "Region",
        "zona": "Zona",
        "sucursal": "Sucursal", "tienda": "Sucursal", "store": "Sucursal",
        "subfamilia": "SubFamilia", "sub familia": "SubFamilia", "origen": "SubFamilia",
        "unidades stock final": "Unidades Stock Final", "stock final unidades": "Unidades Stock Final",
        "stock final": "Unidades Stock Final", "stock (unidades)": "Unidades Stock Final",
        "unidades vendidas": "Unidades Vendidas", "ventas unidades": "Unidades Vendidas", "ventas": "Unidades Vendidas",
    }
    REQUIRED_NORM = [norm(x) for x in REQUIRED]
    ALIASES_NORM = {k: v for k, v in ALIASES.items()}

    best = (-1, -1, None)  # (matches, row_idx, cols_map)
    nrows = min(len(df_no_header), max_scan)

    for i in range(nrows):
        row = list(df_no_header.iloc[i].values)
        cols_map = []
        matches = 0
        for val in row:
            key = norm(val)
            canon = None
            if key in ALIASES_NORM:
                canon = ALIASES_NORM[key]
            elif key in REQUIRED_NORM:
                canon = REQUIRED[REQUIRED_NORM.index(key)]
            cols_map.append(canon)
            if canon in REQUIRED:
                matches += 1
        if matches > best[0]:
            best = (matches, i, cols_map)
        if matches == len(REQUIRED):
            break

    if best[0] >= 5:
        return best[1], best[2]
    return None, None


def _read_excel_header(path: Path, sheet: str | None) -> tuple[list[str], int]:
    """
    Lee solo la cabecera del Excel (primeras ~30 filas) y retorna:
    (nombres_canonicos, fila_datos_inicio)
    """
    p = Path(path)
    target = (sheet if sheet not in (None, "") else 0)
    
    # Leer solo las primeras filas para detectar encabezado
    x = pd.read_excel(p, sheet_name=target, header=None, nrows=100)
    if isinstance(x, dict):
        raw = x[target] if isinstance(target, str) and target in x else next(iter(x.values()))
    else:
        raw = x

    hdr_idx, cols_map = _detect_header_row(raw, max_scan=30)
    if hdr_idx is None:
        raise ValueError("No pude detectar la fila de encabezados. Verificá el archivo/hoja.")

    canon_cols = []
    header_row_values = list(raw.iloc[hdr_idx].values)
    for j, v in enumerate(header_row_values):
        canon = cols_map[j]
        if canon is None:
            canon = str(v).strip() if v is not None else f"col_{j}"
        canon_cols.append(canon)

    # Validar que estén las requeridas
    REQUIRED = ["Dia", "Region", "Zona", "Sucursal", "SubFamilia", "Unidades Stock Final", "Unidades Vendidas"]
    miss = [c for c in REQUIRED if c not in canon_cols]
    if miss:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(miss)}")

    return canon_cols, hdr_idx + 1  # hdr_idx+1 es donde empiezan los datos


def process_navidad_file(path: Path, *, sheet: str | None, pad: int = 0, strict_area: bool = False, chunk_size: int = 10000):
    """
    Lee un Excel en chunks para minimizar uso de RAM usando openpyxl.
    Usa update_or_create para evitar duplicados (sobreescribe si existe).
    
    Args:
        path: Ruta al archivo Excel
        sheet: Nombre o índice de la hoja
        pad: Padding para códigos de sucursal
        strict_area: Validación región/zona
        chunk_size: Cantidad de filas a procesar por iteración (default 10000)
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    # Detectar encabezados leyendo solo primeras filas con pandas
    canon_cols, data_start_row = _read_excel_header(p, sheet)

    summary = {
        "stock_created": 0, "stock_updated": 0, "stock_skipped": 0,
        "sales_created": 0, "sales_updated": 0, "sales_skipped": 0,
        "rows": 0,
        "detected_columns": canon_cols,
        "rows_raw": 0,
    }

    # Cache de Store y Family para evitar queries repetidas
    store_cache = {}
    family_cache = {}

    # Usar openpyxl para leer en chunks sin cargar todo a memoria
    target_sheet = (sheet if sheet not in (None, "") else None)
    wb = load_workbook(p, read_only=True, data_only=True)
    
    if target_sheet is None:
        ws = wb.active
    elif isinstance(target_sheet, int):
        ws = wb.worksheets[target_sheet]
    else:
        ws = wb[target_sheet]

    # Mapear columnas por posición
    col_indices = {col_name: idx for idx, col_name in enumerate(canon_cols)}

    row_count = 0
    for row_idx, row in enumerate(ws.iter_rows(min_row=data_start_row + 1, values_only=True), start=data_start_row + 1):
        row_count += 1
        summary["rows"] += 1
        summary["rows_raw"] += 1

        # Construir diccionario de fila con nombres canonicos
        row_dict = {col_name: row[col_idx] if col_idx < len(row) else None for col_name, col_idx in col_indices.items()}

        dt = parse_date(row_dict["Dia"])
        if not dt:
            continue

        code = zfill_code(row_dict["Sucursal"], pad)
        subfam_excel = str(row_dict["SubFamilia"] or "").strip()
        if not subfam_excel:
            continue

        # Store (con cache)
        if code not in store_cache:
            try:
                store_cache[code] = Store.objects.get(code=code)
            except Store.DoesNotExist:
                store_cache[code] = None

        store = store_cache[code]
        if store is None:
            summary["stock_skipped"] += 1
            summary["sales_skipped"] += 1
            continue

        # Validación opcional región/zona
        if strict_area:
            region_excel = str(row_dict.get("Region", "") or "").strip()
            zona_excel = str(row_dict.get("Zona", "") or "").strip()
            if (store.region.name.strip() != region_excel) or (store.zone.name.strip() != zona_excel):
                summary["stock_skipped"] += 1
                summary["sales_skipped"] += 1
                continue

        # Family por ORIGEN (con cache)
        cache_key = (subfam_excel, "is_active")
        if cache_key not in family_cache:
            try:
                family_cache[cache_key] = Family.objects.get(origen=subfam_excel, is_active=True)
            except (Family.DoesNotExist, Family.MultipleObjectsReturned):
                family_cache[cache_key] = None

        family = family_cache[cache_key]
        if family is None:
            summary["stock_skipped"] += 1
            summary["sales_skipped"] += 1
            continue

        # STOCK: usar update_or_create para evitar duplicados
        stock_units = parse_number(row_dict.get("Unidades Stock Final"))
        if stock_units is not None:
            _, is_new = StockRecord.objects.update_or_create(
                store=store, family=family, date=dt,
                defaults={"stock_units": stock_units, "stock_value": None},
            )
            summary["stock_created"] += int(is_new)
            summary["stock_updated"] += int(not is_new)
        else:
            summary["stock_skipped"] += 1

        # SALES: usar update_or_create para evitar duplicados
        units_sold = parse_number(row_dict.get("Unidades Vendidas"))
        if units_sold is not None and units_sold > 0 and not store.is_distribution_center:
            _, is_new = SalesRecord.objects.update_or_create(
                store=store, family=family, date=dt,
                defaults={"units_sold": units_sold, "revenue": None},
            )
            summary["sales_created"] += int(is_new)
            summary["sales_updated"] += int(not is_new)
        else:
            summary["sales_skipped"] += 1

    wb.close()
    return summary

