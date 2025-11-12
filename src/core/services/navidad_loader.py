from pathlib import Path
from datetime import date
import pandas as pd
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

@transaction.atomic
def process_navidad_file(path: Path, *, sheet: str | None, pad: int = 0, strict_area: bool = False):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    # --- helpers de normalización/encabezados ---
    def norm(s):
        s = "" if s is None else str(s)
        return " ".join(s.replace("\n", " ").strip().lower().split())

    REQUIRED = [
        "Dia", "Region", "Zona", "Sucursal",
        "SubFamilia", "Unidades Stock Final", "Unidades Vendidas"
    ]
    # alias -> nombre canónico
    ALIASES = {
        "día": "Dia",
        "dia": "Dia",
        "fecha": "Dia",

        "region": "Region",
        "región": "Region",

        "zona": "Zona",

        "sucursal": "Sucursal",
        "tienda": "Sucursal",
        "store": "Sucursal",

        "subfamilia": "SubFamilia",
        "sub familia": "SubFamilia",
        "origen": "SubFamilia",  # por si viene así

        "unidades stock final": "Unidades Stock Final",
        "stock final unidades": "Unidades Stock Final",
        "stock final": "Unidades Stock Final",
        "stock (unidades)": "Unidades Stock Final",

        "unidades vendidas": "Unidades Vendidas",
        "ventas unidades": "Unidades Vendidas",
        "ventas": "Unidades Vendidas",
    }
    REQUIRED_NORM = [norm(x) for x in REQUIRED]
    ALIASES_NORM = {k: v for k, v in ALIASES.items()}

    def detect_header_row(df_no_header, max_scan=30):
        """
        Recorre las primeras 'max_scan' filas buscando la fila que contenga
        la mayor cantidad de columnas requeridas (usando aliases).
        Devuelve (row_idx, columns_canonicas) o (None, None) si no encuentra.
        """
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
                    # Si coincide exactamente con requerido normalizado
                    # mapeamos al nombre exacto (posición en REQUIRED_NORM)
                    canon = REQUIRED[REQUIRED_NORM.index(key)]
                cols_map.append(canon)
                if canon in REQUIRED:
                    matches += 1
            if matches > best[0]:
                best = (matches, i, cols_map)

            # si encontramos todos, cortamos
            if matches == len(REQUIRED):
                break

        if best[0] >= 5:  # umbral razonable (al menos 5 de 7)
            return best[1], best[2]
        return None, None

    # === LECTURA ROBUSTA ===
    if p.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        target = (sheet if sheet not in (None, "") else 0)
        x = pd.read_excel(p, sheet_name=target, header=None)
        if isinstance(x, dict):
            # si se pidió por nombre y existe
            if isinstance(target, str) and target in x:
                raw = x[target]
            else:
                raw = next(iter(x.values()))
        else:
            raw = x

        # detectar fila de encabezados
        hdr_idx, cols_map = detect_header_row(raw)
        if hdr_idx is None:
            raise ValueError("No pude detectar la fila de encabezados. Verificá el archivo/hoja.")

        # construir nombres canónicos (donde no haya match, dejamos el valor original)
        canon_cols = []
        header_row_values = list(raw.iloc[hdr_idx].values)
        for j, v in enumerate(header_row_values):
            canon = cols_map[j]
            if canon is None:
                canon = str(v).strip() if v is not None else f"col_{j}"
            canon_cols.append(canon)

        # datos desde la fila siguiente al encabezado
        df = raw.iloc[hdr_idx + 1:].copy()
        df.columns = canon_cols
        df = df.reset_index(drop=True)

        # eliminar columnas completamente vacías
        df = df.dropna(axis=1, how="all")
    else:
        # CSV/TSV: intentamos con encabezado en la primera línea
        # si falla, el usuario debería limpiar el archivo o pasar XLSX
        df = pd.read_csv(p, sep=None, engine="python")
    # === FIN LECTURA ===
    summary_meta = {
            "detected_columns": list(df.columns),
            "rows_raw": int(df.shape[0]),
        }
    # Validar que estén las requeridas (después de normalizar)
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(miss)}")

    summary = {
        "stock_created": 0, "stock_updated": 0, "stock_skipped": 0,
        "sales_created": 0, "sales_updated": 0, "sales_skipped": 0,
        "rows": 0,
    }

    for _, r in df.iterrows():
        summary["rows"] += 1
        dt = parse_date(r["Dia"])
        if not dt:
            continue

        code = zfill_code(r["Sucursal"], pad)
        subfam_excel = str(r["SubFamilia"]).strip()
        if not subfam_excel:
            continue

        # Store
        try:
            store = Store.objects.get(code=code)
        except Store.DoesNotExist:
            summary["stock_skipped"] += 1
            summary["sales_skipped"] += 1
            continue

        # Validación opcional región/zona
        if strict_area:
            region_excel = str(r.get("Region", "") or "").strip()
            zona_excel   = str(r.get("Zona", "") or "").strip()
            if (store.region.name.strip() != region_excel) or (store.zone.name.strip() != zona_excel):
                summary["stock_skipped"] += 1
                summary["sales_skipped"] += 1
                continue

        # Family por ORIGEN == "SubFamilia"
        try:
            family = Family.objects.get(origen=subfam_excel, is_active=True)
        except Family.DoesNotExist:
            summary["stock_skipped"] += 1
            summary["sales_skipped"] += 1
            continue
        except Family.MultipleObjectsReturned:
            summary["stock_skipped"] += 1
            summary["sales_skipped"] += 1
            continue

        # STOCK
        stock_units = parse_number(r.get("Unidades Stock Final"))
        if stock_units is not None:
            _, is_new = StockRecord.objects.update_or_create(
                store=store, family=family, date=dt,
                defaults={"stock_units": stock_units, "stock_value": None},
            )
            summary["stock_created"] += int(is_new)
            summary["stock_updated"] += int(not is_new)
        else:
            summary["stock_skipped"] += 1

        # SALES (omitimos CDR o ventas == 0)
        units_sold = parse_number(r.get("Unidades Vendidas"))
        if units_sold is not None and units_sold > 0 and not store.is_distribution_center:
            _, is_new = SalesRecord.objects.update_or_create(
                store=store, family=family, date=dt,
                defaults={"units_sold": units_sold, "revenue": None},
            )
            summary["sales_created"] += int(is_new)
            summary["sales_updated"] += int(not is_new)
        else:
            summary["sales_skipped"] += 1
            
        summary.update(summary_meta)
    return summary

