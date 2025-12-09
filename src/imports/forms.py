from django import forms

class NavidadUploadForm(forms.Form):
    file = forms.FileField(label="Archivo XLSX/CSV/TSV")
    sheet = forms.CharField(label="Nombre de hoja (si es Excel)", required=False)
    pad = forms.IntegerField(label="Zero-padding del código de sucursal (si aplica)", min_value=0, initial=0, required=False)
    strict_area = forms.BooleanField(label="Validar Región/Zona contra maestro", required=False, initial=False)

    def clean_sheet(self):
        s = self.cleaned_data.get("sheet", "")
        return s.strip()  # "" en vez de None
