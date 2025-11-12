from django.contrib import admin
from .models import SalesRecord

@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ("store", "family", "date", "units_sold", "revenue")
    search_fields = ("store__code", "store__name", "family__familia_std", "family__subfamilia_std")
    list_filter = ("store__region", "store__zone", "store__is_distribution_center")
