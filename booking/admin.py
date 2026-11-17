from django.contrib import admin

from .models import PengaturanSitus, Booking, Rating, FotoGaleri

admin.site.site_header = "Administrasi Akbar Studio Musik"
admin.site.site_title = "Akbar Studio Musik Admin"
admin.site.index_title = "Dashboard"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["nama", "whatsapp", "tanggal", "jam_mulai", "status", "harga", "token", "created_at"]
    list_filter = ["status", "tanggal"]
    search_fields = ["nama", "whatsapp", "token"]
    date_hierarchy = "tanggal"
    readonly_fields = ["token", "created_at"]
    ordering = ["-tanggal", "jam_mulai"]
    actions = ["batalkan_booking"]

    @admin.action(description="Batalkan booking yang dipilih")
    def batalkan_booking(self, request, queryset):
        updated = queryset.filter(status="confirmed").update(status="cancelled")
        self.message_user(request, f"{updated} booking dibatalkan.")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["nama", "nilai", "tampil", "created_at"]
    list_filter = ["tampil", "nilai"]
    search_fields = ["nama", "pesan"]


@admin.register(PengaturanSitus)
class PengaturanSitusAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PengaturanSitus.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FotoGaleri)
class FotoGaleriAdmin(admin.ModelAdmin):
    list_display = ["judul", "foto", "tampil", "tanggal_upload"]
    list_filter = ["tampil", "tanggal_upload"]
    search_fields = ["judul"]