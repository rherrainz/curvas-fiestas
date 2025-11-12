from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from core.models import Region, Zone, Store

class HomeView(TemplateView):
    template_name = 'base.html'

def api_zones_by_region(request):
    region_id = request.GET.get("region_id")
    if not region_id:
        return JsonResponse({"items": []})
    zones = Zone.objects.filter(region_id=region_id).order_by("name").values("id", "name")
    return JsonResponse({"items": list(zones)})

def api_stores_by_zone(request):
    zone_id = request.GET.get("zone_id")
    if not zone_id:
        return JsonResponse({"items": []})
    stores = Store.objects.filter(zone_id=zone_id).order_by("code").values("code", "name")
    # Devolvemos code como id (lo que usa el resto del sistema)
    items = [{"id": s["code"], "label": f'{s["code"]} - {s["name"]}' if s["name"] else s["code"]} for s in stores]
    return JsonResponse({"items": items})

def api_store_info(request):
    code = request.GET.get("code")
    try:
        s = Store.objects.select_related("region","zone").get(code=code)
        return JsonResponse({
            "ok": True,
            "store": {"code": s.code, "name": s.name or ""},
            "region": {"id": s.region_id, "name": s.region.name},
            "zone":   {"id": s.zone_id,   "name": s.zone.name},
        })
    except Store.DoesNotExist:
        return JsonResponse({"ok": False})