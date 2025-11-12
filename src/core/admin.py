from django.contrib import admin
from .models import Region, Zone, Store, Family

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    search_fields = ("name",)

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    list_filter = ("region",)
    search_fields = ("name",)

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "region", "zone", "is_distribution_center")
    list_filter = ("region", "zone", "is_distribution_center")
    search_fields = ("code", "name")

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("origen", "sector", "familia_std", "subfamilia_std", "is_active")
    list_filter = ("is_active", "origen", "sector")
    search_fields = ("origen", "sector", "familia_std", "subfamilia_std")