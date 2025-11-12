from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncDay, ExtractYear
from datetime import timedelta
from core.models import Region, Zone, Store, Family
from stock.models import StockRecord
from .models import SalesRecord
from core.utils.periods import christmas_period

def _apply_scope(filters, request):
    """
    Aplica filtros dinámicos según querystring:
    ?region_id= &zone_id= &store_code= &family_id=
    """
    region_id = request.GET.get("region_id")
    zone_id   = request.GET.get("zone_id")
    store_code= request.GET.get("store_code")
    family_id = request.GET.get("family_id")

    if region_id:
        filters["store__region_id"] = region_id
    if zone_id:
        filters["store__zone_id"] = zone_id
    if store_code:
        filters["store__code"] = store_code
    if family_id:
        filters["family_id"] = family_id
    return filters

def curves_view(request):
    regions = Region.objects.all().order_by("name")
    families = Family.objects.filter(is_active=True).order_by("origen","familia_std","subfamilia_std")
    return render(request, "sales/curves.html", {
        "regions": regions,
        "families": families,
    })

def _years_to_compare(pivot_year: int, available: list[int]) -> list[int]:
    """Devuelve hasta tres años: pivot-2, pivot-1, pivot (en ese orden) filtrando por los que existen."""
    candidates = [pivot_year - 2, pivot_year - 1, pivot_year]
    avail_set = set(int(y) for y in available if y is not None)
    years = [y for y in candidates if y in avail_set]
    return years or sorted(avail_set)[-3:]  # fallback: últimos 3 disponibles

def _available_years():
    y1 = SalesRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    y2 = StockRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    return sorted({int(y) for y in list(y1) + list(y2) if y is not None})

def _coherent_scope_from_request(request):
    """Devuelve un dict con filtros coherentes. Si hay sucursal, fuerza region/zone a las de la sucursal."""
    region_id = request.GET.get("region_id") or None
    zone_id   = request.GET.get("zone_id") or None
    store_code= request.GET.get("store_code") or None
    family_id = request.GET.get("family_id") or None

    scope = {}
    if store_code:
        try:
            st = Store.objects.select_related("region","zone").get(code=store_code)
            scope["store__code"] = st.code
            scope["store__region_id"] = st.region_id
            scope["store__zone_id"] = st.zone_id
        except Store.DoesNotExist:
            # si no existe, ignoramos el store_code; el frontend debería evitar esto
            pass
    else:
        if region_id:
            scope["store__region_id"] = region_id
        if zone_id:
            scope["store__zone_id"] = zone_id

    if family_id:
        scope["family_id"] = family_id

    return scope

def curves_data(request):
    """
    Ventas diarias acumuladas (1/oct–31/dic) comparando 3 años:
    - Si hay sucursal: por esa sucursal.
    - Si no hay sucursal: agregado de la zona/region según filtros.
    Siempre excluye CDR (ventas solo de tiendas).
    """
    pivot_year = int(request.GET.get("year", 2025))
    available = _available_years()
    years = _years_to_compare(pivot_year, available)
    scope = _coherent_scope_from_request(request)

    # Eje X común (MM-DD) para superponer años
    labels = []
    # armamos para cualquier año (usamos el pivot para construir fechas y luego mostramos MM-DD)
    start, end = christmas_period(pivot_year)
    cur = start
    while cur <= end:
        labels.append(cur.strftime("%m-%d"))
        cur += timedelta(days=1)

    datasets = []
    for y in years:
        s, e = christmas_period(y)
        filters = {"date__range": (s, e), "store__is_distribution_center": False}
        filters.update(scope)

        daily = (SalesRecord.objects
                 .filter(**filters)
                 .annotate(d=TruncDay("date"))
                 .values("d")
                 .annotate(units=Sum("units_sold"))
                 .order_by("d"))

        # mapa fecha->unidades
        m = {row["d"]: float(row["units"] or 0) for row in daily}

        # construir serie diaria en orden y acumular
        cur = s
        series = []
        acc = 0.0
        while cur <= e:
            acc += m.get(cur, 0.0)
            series.append(acc)
            cur += timedelta(days=1)

        # ⬇️ nuevo: no enviar series sin datos reales
        if sum(series) <= 0:
            continue

        datasets.append({
            "label": f"Ventas acumuladas {y}",
            "data": series,
        })

    return JsonResponse({
        "labels": labels,  # ["10-01","10-02",...,"12-31"]
        "datasets": datasets,
        "meta": {
            "pivot_year": pivot_year,
            "years_compared": years,
            "available_years": available,
            "scope": {
                "region_id": request.GET.get("region_id"),
                "zone_id": request.GET.get("zone_id"),
                "store_code": request.GET.get("store_code"),
                "family_id": request.GET.get("family_id"),
            },
            "note": "Si se elige sucursal, región/zona se fuerzan a la de esa sucursal."
        }
    })