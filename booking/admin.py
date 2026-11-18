from django.contrib import admin
from django.db.models import OuterRef, Subquery, Count, Sum, Min
from django.utils.html import format_html

from .models import PengaturanSitus, Booking, Rating, FotoGaleri

admin.site.site_header = "Administrasi Akbar Studio Musik"
admin.site.site_title = "Akbar Studio Musik Admin"
admin.site.index_title = "Dashboard"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["nama", "tanggal", "jam_range", "durasi", "total_harga", "wa_link", "status_badge", "token"]
    list_filter = ["status", "tanggal"]
    search_fields = ["nama", "whatsapp", "token"]
    date_hierarchy = "tanggal"
    readonly_fields = ["token", "created_at"]
    ordering = ["-tanggal", "jam_mulai"]
    list_per_page = 25
    actions = ["batalkan_booking", "hapus_grup_token"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        first_ids = (
            qs.values("token")
            .annotate(first_id=Min("id"))
            .values_list("first_id", flat=True)
        )
        qs = qs.filter(id__in=first_ids)

        token_rows = Booking.objects.filter(token=OuterRef("token"))
        qs = qs.annotate(
            durasi=Subquery(
                token_rows.values("token").annotate(c=Count("id")).values("c")[:1]
            ),
            total_harga=Subquery(
                token_rows.values("token").annotate(s=Sum("harga")).values("s")[:1]
            ),
            jam_mulai_awal=Subquery(
                token_rows.order_by("jam_mulai").values("jam_mulai")[:1]
            ),
        )
        return qs

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    @admin.display(description="Durasi", ordering="durasi")
    def durasi(self, obj):
        return f"{obj.durasi} jam"

    @admin.display(description="Jam", ordering="jam_mulai_awal")
    def jam_range(self, obj):
        mulai = obj.jam_mulai_awal
        selesai = mulai + obj.durasi
        return f"{mulai:02d}.00 - {selesai:02d}.00"

    @admin.display(description="Total", ordering="total_harga")
    def total_harga(self, obj):
        return "Rp" + f"{int(obj.total_harga):,}".replace(",", ".")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        first_ids = (
            qs.values("token")
            .annotate(first_id=Min("id"))
            .values_list("first_id", flat=True)
        )
        qs = qs.filter(id__in=first_ids)

        token_rows = Booking.objects.filter(token=OuterRef("token"))
        qs = qs.annotate(
            durasi=Subquery(
                token_rows.values("token").annotate(c=Count("id")).values("c")[:1]
            ),
            total_harga=Subquery(
                token_rows.values("token").annotate(s=Sum("harga")).values("s")[:1]
            ),
            jam_mulai_awal=Subquery(
                token_rows.order_by("jam_mulai").values("jam_mulai")[:1]
            ),
        )
        return qs

    @admin.display(description="Durasi", ordering="durasi")
    def durasi(self, obj):
        return f"{obj.durasi} jam"

    @admin.display(description="Jam", ordering="jam_mulai_awal")
    def jam_range(self, obj):
        mulai = obj.jam_mulai_awal
        selesai = mulai + obj.durasi
        return f"{mulai:02d}.00 - {selesai:02d}.00"

    @admin.display(description="Total", ordering="total_harga")
    def total_harga(self, obj):
        return "Rp" + f"{int(obj.total_harga):,}".replace(",", ".")

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        warna = {"confirmed": "#1f9d55", "cancelled": "#d7141f"}.get(obj.status, "#6b6e75")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:3px;'
            'font-size:11px;letter-spacing:.08em;text-transform:uppercase">{}</span>',
            warna, obj.status,
        )

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

    @admin.action(description="Hapus semua slot dengan token yang sama")
    def hapus_grup_token(self, request, queryset):
        tokens = set(queryset.values_list("token", flat=True))
        jumlah_dihapus = 0
        for token in tokens:
            count = Booking.objects.filter(token=token).count()
            Booking.objects.filter(token=token).delete()
            jumlah_dihapus += count
        self.message_user(
            request,
            f"{jumlah_dihapus} slot booking ({len(tokens)} grup token) dihapus.",
        )


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