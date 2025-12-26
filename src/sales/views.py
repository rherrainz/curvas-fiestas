from datetime import date, timedelta

from django.db.models import Max, Sum
from django.db.models.functions import ExtractYear, TruncDay
from django.http import JsonResponse
from django.shortcuts import render

from core.models import Family, Region, Store, Zone
from core.utils.periods import christmas_period
from stock.models import StockRecord

from .models import SalesRecord


def _apply_scope(filters, request):
    """
    Aplica filtros dinamicos segun querystring:
    ?region_id= &zone_id= &store_code= &family_id=
    """
    region_id = request.GET.get("region_id")
    zone_id = request.GET.get("zone_id")
    store_code = request.GET.get("store_code")
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
    families = Family.objects.filter(is_active=True).order_by("origen", "familia_std", "subfamilia_std")
    return render(request, "sales/curves.html", {
        "regions": regions,
        "families": families,
    })


# ---------------------------
# Ventas por sucursal dentro de una zona (ultimo ano disponible)
# ---------------------------

def sales_by_zone_view(request):
    zones = Zone.objects.order_by("name")
    families = Family.objects.filter(is_active=True).order_by("origen", "familia_std", "subfamilia_std")
    default_zone = zones.first()
    return render(request, "sales/by_zone.html", {
        "zones": zones,
        "families": families,
        "default_zone_id": default_zone.id if default_zone else "",
    })


def sales_by_zone_data(request):
    zone_id = request.GET.get("zone_id")
    family_id = request.GET.get("family_id") or None

    # zona por defecto = primera por nombre
    if not zone_id:
        default_zone = Zone.objects.order_by("name").first()
        if not default_zone:
            return JsonResponse({"labels": [], "data": [], "meta": {"note": "No hay zonas definidas."}})
        zone_id = default_zone.id

    pivot_year = _latest_sales_year()
    if not pivot_year:
        return JsonResponse({"labels": [], "data": [], "meta": {"note": "Sin datos de ventas."}})

    start, end = christmas_period(pivot_year)
    # limitar el fin al ultimo dia con datos en el ano pivot
    max_date = (
        SalesRecord.objects
        .filter(store__zone_id=zone_id, date__year=pivot_year)
        .aggregate(Max("date"))
        .get("date__max")
    )
    end_date = max_date if max_date and max_date >= start else end

    filters = {
        "store__zone_id": zone_id,
        "store__is_distribution_center": False,
        "date__range": (start, end_date),
    }
    if family_id:
        filters["family_id"] = family_id

    # ventas diarias por sucursal
    daily = (
        SalesRecord.objects
        .filter(**filters)
        .values("store_id", "store__code", "store__name", "date")
        .annotate(units=Sum("units_sold"))
    )

    # eje X (MM-DD)
    labels = []
    cur = start
    while cur <= end_date:
        labels.append(cur.strftime("%m-%d"))
        cur += timedelta(days=1)

    # agrupar por store
    store_data = {}
    for row in daily:
        sid = row["store_id"]
        info = store_data.setdefault(sid, {
            "label": f"{row['store__code']} - {row['store__name']}".strip(" -"),
            "map": {},
        })
        info["map"][row["date"]] = float(row["units"] or 0)

    datasets = []
    total_units = 0.0
    for sid, info in store_data.items():
        series = []
        acc = 0.0
        cur = start
        while cur <= end_date:
            acc += info["map"].get(cur, 0.0)
            series.append(acc)
            cur += timedelta(days=1)
        if sum(series) <= 0:
            continue
        total_units += series[-1] if series else 0.0
        datasets.append({
            "label": info["label"],
            "data": series,
        })

    zone_name = ""
    try:
        zone_name = Zone.objects.get(id=zone_id).name
    except Zone.DoesNotExist:
        pass

    return JsonResponse({
        "labels": labels,
        "datasets": datasets,
        "meta": {
            "zone_id": zone_id,
            "zone_name": zone_name,
            "pivot_year": pivot_year,
            "start_date": start.isoformat(),
            "end_date": end_date.isoformat(),
            "family_id": family_id,
            "total_units": total_units,
            "note": "Ventas acumuladas por sucursal dentro de la zona en el ultimo ano disponible.",
        }
    })


def _years_to_compare(pivot_year: int, available: list[int]) -> list[int]:
    """Devuelve hasta tres anos: pivot-2, pivot-1, pivot (en ese orden) filtrando por los que existen."""
    candidates = [pivot_year - 2, pivot_year - 1, pivot_year]
    avail_set = set(int(y) for y in available if y is not None)
    years = [y for y in candidates if y in avail_set]
    return years or sorted(avail_set)[-3:]  # fallback: ultimos 3 disponibles


def _available_years():
    y1 = SalesRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    y2 = StockRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    return sorted({int(y) for y in list(y1) + list(y2) if y is not None})


def _latest_sales_year():
    vals = SalesRecord.objects.annotate(y=ExtractYear("date")).values_list("y", flat=True)
    years = [int(v) for v in vals if v is not None]
    return max(years) if years else None


def _coherent_scope_from_request(request):
    """Devuelve un dict con filtros coherentes. Si hay sucursal, fuerza region/zone a las de la sucursal."""
    region_id = request.GET.get("region_id") or None
    zone_id = request.GET.get("zone_id") or None
    store_code = request.GET.get("store_code") or None
    family_id = request.GET.get("family_id") or None

    scope = {}
    if store_code:
        try:
            st = Store.objects.select_related("region", "zone").get(code=store_code)
            scope["store__code"] = st.code
            scope["store__region_id"] = st.region_id
            scope["store__zone_id"] = st.zone_id
        except Store.DoesNotExist:
            # si no existe, ignoramos el store_code; el frontend deberia evitar esto
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
    Ventas diarias acumuladas (1/oct-31/dic) comparando 3 anos:
    - Si hay sucursal: por esa sucursal.
    - Si no hay sucursal: agregado de la zona/region segun filtros.
    Siempre excluye CDR (ventas solo de tiendas).
    """
    pivot_year = int(request.GET.get("year", 2025))
    available = _available_years()
    years = _years_to_compare(pivot_year, available)
    scope = _coherent_scope_from_request(request)

    # Eje X comun (MM-DD) para superponer anos
    labels = []
    # armamos para cualquier ano (usamos el pivot para construir fechas y luego mostramos MM-DD)
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

        # nuevo: no enviar series sin datos reales
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
            "note": "Si se elige sucursal, region/zona se fuerzan a la de esa sucursal."
        }
    })


# ---------------------------
# Estado de ventas 2025 (pivot = ultimo dia cargado 2025)
# ---------------------------

def _default_region_id():
    first = Region.objects.order_by("name").first()
    return first.id if first else None


def status_overview_view(request):
    regions = Region.objects.order_by("name")
    default_region_id = _default_region_id()
    return render(request, "sales/status_overview.html", {
        "regions": regions,
        "default_region_id": default_region_id or "",
    })


def _store_sort_key(st):
    code = st.get("code") or ""
    try:
        return (0, int(code))
    except (TypeError, ValueError):
        return (1, str(code))


def _pivot_range_2025(region_id: int | str | None):
    pivot_year = 2025
    start = date(pivot_year, 10, 1)
    qs = SalesRecord.objects.filter(
        store__is_distribution_center=False,
        date__year=pivot_year,
    )
    if region_id:
        qs = qs.filter(store__region_id=region_id)
    end = qs.aggregate(Max("date")).get("date__max")
    if not end or end < start:
        return None, None
    length = (end - start).days + 1
    prev_start = date(pivot_year - 1, start.month, start.day)
    prev_end = prev_start + timedelta(days=length - 1)
    return (start, end), (prev_start, prev_end)


def _collect_units_by(scope_filters, date_range):
    """Devuelve mapa {(family_id, entity_id): units}."""
    group_field = scope_filters.pop("_group_field")
    qs = (SalesRecord.objects
          .filter(**scope_filters, date__range=date_range)
          .values("family_id", group_field)
          .annotate(units=Sum("units_sold")))
    data = {}
    for row in qs:
        fid = row["family_id"]
        eid = row[group_field]
        data[(fid, eid)] = float(row["units"] or 0)
    return data


def status_overview_data(request):
    region_id = request.GET.get("region_id") or _default_region_id()
    zone_id = request.GET.get("zone_id") or None

    if not region_id:
        return JsonResponse({"rows": [], "columns": [], "families": [], "meta": {"note": "No hay regiones definidas."}})

    pivot_range, prev_range = _pivot_range_2025(region_id)
    if not pivot_range:
        return JsonResponse({"rows": [], "columns": [], "families": [], "meta": {"note": "Sin datos 2025 para la region seleccionada."}})

    start, end = pivot_range
    prev_start, prev_end = prev_range

    families = list(Family.objects.filter(is_active=True).order_by("origen", "familia_std", "subfamilia_std"))

    mode = "zone" if not zone_id else "store"
    if mode == "zone":
        entities = list(Zone.objects.filter(region_id=region_id).order_by("name").values("id", "name"))
        group_field = "store__zone_id"
        scope = {"store__region_id": region_id, "store__is_distribution_center": False, "_group_field": group_field}
    else:
        store_qs = Store.objects.filter(zone_id=zone_id, is_distribution_center=False).values("id", "code", "name")
        entities = sorted(store_qs, key=_store_sort_key)
        group_field = "store_id"
        scope = {"store__zone_id": zone_id, "store__is_distribution_center": False, "_group_field": group_field}

    current_map = _collect_units_by(scope.copy(), (start, end))
    previous_map = _collect_units_by(scope.copy(), (prev_start, prev_end))

    def fmt_family_label(f: Family):
        return " / ".join(filter(None, [f.origen, f.familia_std, f.subfamilia_std]))

    columns = []
    if mode == "zone":
        columns = [{"id": z["id"], "label": z["name"]} for z in entities]
    else:
        for st in entities:
            code = (st.get("code") or "").strip()
            name = (st.get("name") or "").strip()
            label = code or name or str(st["id"])
            columns.append({"id": st["id"], "label": label})

    rows = []
    for f in families:
        cells = []
        for col in columns:
            cur = current_map.get((f.id, col["id"]), 0.0)
            prev = previous_map.get((f.id, col["id"]), 0.0)
            delta_units = cur - prev
            pct = None if prev == 0 else ((cur / prev) - 1) * 100
            cells.append({
                "entity_id": col["id"],
                "pct": pct,
                "delta_units": delta_units,
                "current": cur,
                "previous": prev,
            })
        rows.append({
            "family_id": f.id,
            "family_label": fmt_family_label(f),
            "cells": cells,
        })

    return JsonResponse({
        "columns": columns,
        "families": [{"id": f.id, "label": fmt_family_label(f)} for f in families],
        "rows": rows,
        "meta": {
            "mode": mode,
            "region_id": region_id,
            "zone_id": zone_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "prev_start_date": prev_start.isoformat(),
            "prev_end_date": prev_end.isoformat(),
            "note": "Corte al ultimo dia con datos en 2025; compara contra mismo rango de 2024.",
        }
    })
