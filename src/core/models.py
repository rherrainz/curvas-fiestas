from django.db import models

class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Zone(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = (("region", "name"),)
        ordering = ["region__name", "name"]

    def __str__(self):
        return f"{self.region} / {self.name}"


class Store(models.Model):
    code = models.CharField(max_length=10, unique=True)  # ej: "035", "CDR01"
    name = models.CharField(max_length=150)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="stores")
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="stores")
    is_distribution_center = models.BooleanField(default=False)  # CDR: stock sí, ventas no

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["region", "zone"]),
        ]
        ordering = ["code"]

    def __str__(self):
        suffix = " (CDR)" if self.is_distribution_center else ""
        return f"{self.code} - {self.name}{suffix}"

class Family(models.Model):
    origen = models.CharField(max_length=80)
    sector = models.CharField(max_length=80)
    familia_std = models.CharField(max_length=120)
    subfamilia_std = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("origen", "sector", "familia_std", "subfamilia_std"),)
        ordering = ["origen", "sector", "familia_std", "subfamilia_std"]

    def __str__(self):
        return f"{self.origen} • {self.sector} • {self.familia_std} • {self.subfamilia_std}"