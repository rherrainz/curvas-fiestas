from django.db import models
from core.models import Store, Family

class StockRecord(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="stock")
    family = models.ForeignKey(Family, on_delete=models.PROTECT, related_name="stock")
    date = models.DateField()  # día del stock (si es mensual, usamos día 1)
    stock_units = models.DecimalField(max_digits=14, decimal_places=2)          # unidades
    stock_value = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)  # $ opcional

    class Meta:
        unique_together = (("store", "family", "date"),)
        indexes = [
            models.Index(fields=["store", "family", "date"]),  # composite key lookup en flush_chunk
            models.Index(fields=["store", "date"]),
            models.Index(fields=["family", "date"]),
            models.Index(fields=["date"]),  # análisis por fecha
        ]
        ordering = ["store__code", "family__familia_std", "family__subfamilia_std", "date"]

    def __str__(self):
        return f"{self.store.code} | {self.family} | {self.date} | {self.stock_units}"
