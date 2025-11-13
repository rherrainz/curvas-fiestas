from datetime import date, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import ExtractYear

from core.models import Region, Zone, Store, Family
from core.utils.periods import christmas_period
from sales.models import SalesRecord
from stock.models import StockRecord


def _safe_int(x, default):
    try:
        return int(x)
    except Exception:
        return default

def _target_dates(pivot_year:int, mm:int, dd:int):
    # fechas equivalentes (misma MM-DD) en pivot, pivot-1, pivot-2, si están dentro del período
    out = []
    for y in [pivot_year-2, pivot_year-1, pivot_year]:
        s, e = christmas_period(y)
        try:
            d = date(y, mm, dd)
        except ValueError:
            continue
        if s <= d <= e:
            out.append((y, d))
    return out  # orden cronológico ascendente

def overview_view(request):
    # UI: filtros en cascada + fecha (por defecto hoy si está en período, si no, último día del período del último año con datos)
    regions = Region.objects.order_by("name")
    families = Family.objects.filter(is_active=True).order_by("origen","familia_std","subfamilia_std")
    return render(request, "insights/overview.html", {
        "regions": regions,
        "families": families,
    })


def _safe_int(x, default):
    try:
        return int(x)
    except Exception:
        return default


def overview_data(request):
    """
    Devuelve una tabla a nivel de FAMILIA:

    SubFamilia | UV Act Acum | Stock Actual | Stk + Vta Act Acum |
    UV Totales Año Ant | Stk+Vta Act / UV Ant | UV Act/Ant
    """

    region_id = request.GET.get("region_id") or None
    zone_id   = request.GET.get("zone_id") or None
    store_code= request.GET.get("store_code") or None
    source    = request.GET.get("source", "all")  # all|stores|cdr
    cut_str   = request.GET.get("cut_date") or None  # YYYY-MM-DD

    # ---------- Año pivot y períodos ----------
    y_sales = SalesRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    y_stock = StockRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    avail_years = sorted({int(y) for y in list(y_sales) + list(y_stock) if y is not None})
    pivot = avail_years[-1] if avail_years else date.today().year
    prev_year = pivot - 1

    s_act, e_act   = christmas_period(pivot)
    s_prev, e_prev = christmas_period(prev_year)

    # ---------- Fecha de corte (default = ayer) ----------
    yesterday = date.today() - timedelta(days=1)

    if cut_str:
        try:
            t = date.fromisoformat(cut_str)
        except ValueError:
            t = yesterday
    else:
        t = yesterday

    # forzamos año pivot
    try:
        target = date(pivot, t.month, t.day)
    except ValueError:
        target = e_act

    # clamp al período navideño
    if target < s_act:
        target = s_act
    if target > e_act:
        target = e_act

    # ---------- Filtros de ámbito (Store) ----------
    base = {}

    if store_code:
        # Si filtra por sucursal, usamos solo esa sucursal (pero igual agregamos por FAMILIA)
        try:
            st = Store.objects.get(code=store_code)
            base["store__code"]      = st.code
            base["store__region_id"] = st.region_id
            base["store__zone_id"]   = st.zone_id
        except Store.DoesNotExist:
            return JsonResponse({"rows": [], "meta": {"pivot": pivot, "cut_date": target.isoformat()}})
    else:
        if region_id:
            base["store__region_id"] = region_id
        if zone_id:
            base["store__zone_id"]   = zone_id

    if source == "stores":
        base["store__is_distribution_center"] = False
    elif source == "cdr":
        base["store__is_distribution_center"] = True

    # ---------- 1) UV Act Acum (año pivot, 1/oct -> target) ----------
    s_act_start, _ = christmas_period(pivot)
    sales_act_qs = (
        SalesRecord.objects
        .filter(date__range=(s_act_start, target), **base)
        .values("family__id", "family__origen")
        .annotate(units=Sum("units_sold"))
    )

    sales_act_map = {}
    for r in sales_act_qs:
        fid = r["family__id"]
        sales_act_map[fid] = float(r["units"] or 0)

    # ---------- 2) Stock Actual (día target, año pivot) ----------
    stock_act_qs = (
        StockRecord.objects
        .filter(date=target, **base)
        .values("family__id", "family__origen")
        .annotate(units=Sum("stock_units"))
    )

    stock_act_map = {}
    for r in stock_act_qs:
        fid = r["family__id"]
        stock_act_map[fid] = float(r["units"] or 0)

    # ---------- 3) UV Totales Año Anterior (1/oct -> 31/dic) ----------
    sales_prev_qs = (
        SalesRecord.objects
        .filter(date__range=(s_prev, e_prev), **base)
        .values("family__id", "family__origen")
        .annotate(units=Sum("units_sold"))
    )

    sales_prev_map = {}
    for r in sales_prev_qs:
        fid = r["family__id"]
        sales_prev_map[fid] = float(r["units"] or 0)

    # ---------- 4) Siempre mostramos TODAS las familias activas ----------
    families = Family.objects.filter(is_active=True).order_by("origen")

    rows = []
    for fam in families:
        fid    = fam.id
        subfam = fam.origen

        uv_act   = sales_act_map.get(fid, 0.0)
        stk_act  = stock_act_map.get(fid, 0.0)
        stk_plus = uv_act + stk_act
        uv_prev  = sales_prev_map.get(fid, 0.0)

        if uv_prev > 0:
            ratio_stkplus_vs_prev = stk_plus / uv_prev
            ratio_uv_act_vs_prev  = uv_act / uv_prev
        else:
            ratio_stkplus_vs_prev = None
            ratio_uv_act_vs_prev  = None

        rows.append({
            "subfamily": subfam,
            "uv_act_cum": uv_act,
            "stock_act": stk_act,
            "stock_plus_uv_act": stk_plus,
            "uv_prev_total": uv_prev,
            "ratio_stkplus_vs_prev": ratio_stkplus_vs_prev,
            "ratio_uv_act_vs_prev": ratio_uv_act_vs_prev,
        })

    return JsonResponse({
        "meta": {
            "pivot_year": pivot,
            "prev_year": prev_year,
            "cut_date": target.isoformat(),
            "note": "UV Act: 1/oct–fecha corte año actual (agregado por familia). UV Ant: 1/oct–31/dic año anterior.",
        },
        "rows": rows,
    })