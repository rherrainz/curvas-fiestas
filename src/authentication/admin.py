from django.contrib import admin
from .models import LoginToken

@admin.register(LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'expires_at', 'used', 'used_at')
    list_filter = ('used', 'created_at')
    search_fields = ('email', 'token')
    readonly_fields = ('token', 'created_at', 'used_at')
    
    fieldsets = (
        ('Información del Token', {
            'fields': ('email', 'token', 'user', 'created_at')
        }),
        ('Expiración', {
            'fields': ('expires_at',)
        }),
        ('Estado', {
            'fields': ('used', 'used_at')
        }),
    )

    def has_add_permission(self, request):
        return False  # No se crean manualmente desde admin
