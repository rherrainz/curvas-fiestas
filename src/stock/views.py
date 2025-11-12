from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncDay, ExtractYear, TruncDate
from datetime import timedelta
from core.models import Region, Zone, Store, Family
from core.utils.periods import christmas_period
from .models import StockRecord
from sales.models import SalesRecord  # para available years conjunto

def _available_years():
    y1 = StockRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    y2 = SalesRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    return sorted({int(y) for y in list(y1)+list(y2) if y is not None})

def _years_to_compare(pivot, available):
    cand = [pivot-2, pivot-1, pivot]
    avail = set(available)
    res = [y for y in cand if y in avail]
    return res or sorted(avail)[-3:]

def _coherent_scope_from_request(request):
    region_id = request.GET.get("region_id") or None
    zone_id   = request.GET.get("zone_id") or None
    store_code= request.GET.get("store_code") or None
    family_id = request.GET.get("family_id") or None
    scope = {}
    if store_code:
        try:
            st = Store.objects.select_related("region","zone").get(code=store_code)
            scope["store__code"]      = st.code         # fuerza coherencia
            scope["store__region_id"] = st.region_id
            scope["store__zone_id"]   = st.zone_id
        except Store.DoesNotExist:
            pass
    else:
        if region_id: scope["store__region_id"] = region_id
        if zone_id:   scope["store__zone_id"]   = zone_id
    if family_id:     scope["family_id"]        = family_id

    for k, v in list(scope.items()):
        if v in (None, "", "None"):
            scope.pop(k)

    return scope

def stock_curves_view(request):
    return render(request, "stock/curves.html", {
        "regions":  Region.objects.order_by("name"),
        "zones":    Zone.objects.none(),  # se cargan por JS
        "stores":   Store.objects.none(), # idem
        "families": Family.objects.filter(is_active=True).order_by("origen","familia_std","subfamilia_std"),
        "default_source": request.GET.get("source") or "all",  # all|stores|cdr
    })

def stock_curves_data(request):
    # Pivote = último año con datos; NO hay selector de año en UI
    available = _available_years()
    pivot = available[-1] if available else 2025
    years = _years_to_compare(pivot, available)

    source = request.GET.get("source", "all")  # all|stores|cdr
    scope  = _coherent_scope_from_request(request)

    # eje X fijo (MM-DD)
    s_p, e_p = christmas_period(pivot)
    labels = []
    cur = s_p
    while cur <= e_p:
        labels.append(cur.strftime("%m-%d"))
        cur += timedelta(days=1)

    datasets = []
    for y in years:
        s, e = christmas_period(y)
        filters = {"date__range": (s, e)}
        filters.update(scope)
        if source == "stores":
            filters["store__is_distribution_center"] = False
        elif source == "cdr":
            filters["store__is_distribution_center"] = True

        qs = (StockRecord.objects
            .filter(**filters)
            .values("date")                 # ⬅️ agrupa por la fecha directa
            .annotate(units=Sum("stock_units"))
            .order_by("date"))

        day_map = {row["date"]: float(row["units"] or 0) for row in qs}
        series, cur = [], s
        while cur <= e:
            series.append(day_map.get(cur, 0.0))  # stock diario (no acumulado)
            cur += timedelta(days=1)

        if sum(series) <= 0:  # oculta series planas
            continue

        datasets.append({"label": f"Stock diario {y}", "data": series})

    return JsonResponse({
        "labels": labels,
        "datasets": datasets,
        "meta": {
            "years_compared": years,
            "available_years": available,
            "source": source,
            "note": "Si se elige sucursal, región/zona se fuerzan a la de esa sucursal."
        }
    })
