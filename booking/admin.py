from django.contrib import admin
from django.utils.html import format_html

from .models import PengaturanSitus, Booking, Rating, FotoGaleri

admin.site.site_header = "Administrasi Akbar Studio Musik"
admin.site.site_title = "Akbar Studio Musik Admin"
admin.site.index_title = "Dashboard"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["nama", "wa_link", "tanggal", "jam_mulai", "status_badge", "harga_rp", "created_at"]
    list_filter = ["status", "tanggal"]
    search_fields = ["nama", "whatsapp", "token"]
    date_hierarchy = "tanggal"
    readonly_fields = ["token", "created_at"]
    ordering = ["-tanggal", "jam_mulai"]
    list_per_page = 25
    actions = ["batalkan_booking"]

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        warna = {"confirmed": "#1f9d55", "cancelled": "#d7141f"}.get(obj.status, "#6b6e75")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:3px;'
            'font-size:11px;letter-spacing:.08em;text-transform:uppercase">{}</span>',
            warna, obj.status,
        )

    @admin.display(description="Harga", ordering="harga")
    def harga_rp(self, obj):
        return "Rp" + f"{int(obj.harga):,}".replace(",", ".")

    @admin.display(description="WhatsApp")
    def wa_link(self, obj):
        nomor = "".join(c for c in obj.whatsapp if c.isdigit())
        if nomor.startswith("0"):
            nomor = "62" + nomor[1:]
        return format_html(
            '<a href="https://wa.me/{}" target="_blank" rel="noopener">{}</a>',
            nomor, obj.whatsapp,
        )

    @admin.action(description="Batalkan booking yang dipilih")
    def batalkan_booking(self, request, queryset):
        updated = queryset.filter(status="confirmed").update(status="cancelled")
        self.message_user(request, f"{updated} booking dibatalkan.")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["nama", "bintang", "tampil", "created_at"]
    list_editable = ["tampil"]
    list_filter = ["tampil", "nilai"]
    search_fields = ["nama", "pesan"]

    @admin.display(description="Nilai", ordering="nilai")
    def bintang(self, obj):
        return "★" * obj.nilai + "☆" * (5 - obj.nilai)


@admin.register(PengaturanSitus)
class PengaturanSitusAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PengaturanSitus.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FotoGaleri)
class FotoGaleriAdmin(admin.ModelAdmin):
    list_display = ["thumbnail", "judul", "tampil", "tanggal_upload"]
    list_display_links = ["thumbnail", "judul"]
    list_editable = ["tampil"]
    list_filter = ["tampil", "tanggal_upload"]
    search_fields = ["judul"]

    @admin.display(description="Foto")
    def thumbnail(self, obj):
        if not obj.foto:
            return "-"
        return format_html('<img src="{}" style="height:48px;border-radius:3px">', obj.foto.url)