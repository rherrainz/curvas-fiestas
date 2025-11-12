import os
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .forms import NavidadUploadForm
from core.services.navidad_loader import process_navidad_file

@require_http_methods(["GET", "POST"])
def navidad_upload_view(request):
    context = {"result": None}
    if request.method == "POST":
        form = NavidadUploadForm(request.POST, request.FILES)
        if form.is_valid():
            up_file = form.cleaned_data["file"]
            sheet = form.cleaned_data.get("sheet") or "" 
            pad = form.cleaned_data.get("pad") or 0
            strict_area = form.cleaned_data.get("strict_area") or False

            # guardar temporal
            uploads_dir = Path(settings.MEDIA_ROOT) / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = uploads_dir / up_file.name

            with open(tmp_path, "wb+") as dest:
                for chunk in up_file.chunks():
                    dest.write(chunk)

            try:
                summary = process_navidad_file(tmp_path, sheet=sheet, pad=pad, strict_area=strict_area)
                context["result"] = summary
                messages.success(request, "Archivo procesado correctamente.")
            except Exception as e:
                messages.error(request, f"Error procesando el archivo: {e}")
            finally:
                # limpia archivo temporal
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            messages.error(request, "Revisá los datos del formulario.")
        return render(request, "imports/upload.html", {"form": form, **context})

    # GET
    return render(request, "imports/upload.html", {"form": NavidadUploadForm(), **context})
