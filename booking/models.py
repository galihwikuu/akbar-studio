import secrets
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

KARAKTER_TOKEN = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def buat_token():
    return "".join(secrets.choice(KARAKTER_TOKEN) for _ in range(8))


class Booking(models.Model):
    STATUS_CHOICES = [
        ("confirmed", "Dikonfirmasi"),
        ("cancelled", "Dibatalkan"),
    ]

    nama = models.CharField(max_length=100)
    whatsapp = models.CharField(max_length=20)
    tanggal = models.DateField()
    jam_mulai = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="confirmed")
    harga = models.PositiveIntegerField(default=settings.HARGA_PER_JAM)
    token = models.CharField(max_length=8, db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tanggal", "jam_mulai"]
        constraints = [
            models.UniqueConstraint(
                fields=["tanggal", "jam_mulai"],
                condition=Q(status="confirmed"),
                name="unique_tanggal_jam_aktif",
            )
        ]

    def __str__(self):
        return f"{self.nama} - {self.tanggal} {self.label_jam}"

    @property
    def label_jam(self):
        return f"{self.jam_mulai:02d}.00 - {self.jam_mulai + 1:02d}.00"

    @property
    def waktu_mulai(self):
        return timezone.make_aware(datetime.combine(self.tanggal, time(self.jam_mulai)))

    @property
    def waktu_selesai(self):
        return self.waktu_mulai + timedelta(hours=1)

    @property
    def sudah_selesai(self):
        return timezone.now() >= self.waktu_selesai

    def bisa_dibatalkan(self):
        return (
            self.status == "confirmed"
            and not self.sudah_selesai
            and timezone.now() <= self.waktu_mulai - timedelta(hours=1)
        )


class Rating(models.Model):
    nama = models.CharField(max_length=60, default="Anonim")
    nilai = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    pesan = models.CharField(max_length=300, blank=True)
    tampil = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama}: {self.nilai}"

TENTANG_DEFAULT = "Akbar Musik Studio adalah tempat latihan musik nyaman di Gemolong, Sragen. Kami menyediakan ruang rehearsal band dan jam session dengan fasilitas lengkap serta akustik yang mendukung. Sewa dilakukan per jam tanpa perlu membuat akun, dan pembayaran dapat dilakukan langsung di tempat. Studio buka setiap hari dari pukul 07.00 hingga 22.00 WIB. Kami siap mendampingi perjalanan musikal Anda dengan nyaman dan terjangkau."

class PengaturanSitus(models.Model):
    foto_hero = models.ImageField(upload_to="hero/", blank=True)
    tentang = models.TextField("Teks tentang studio", default=TENTANG_DEFAULT, blank=True)

    class Meta:
        verbose_name = "Pengaturan situs"
        verbose_name_plural = "Pengaturan situs"

    def __str__(self):
        return "Pengaturan situs"


class FotoGaleri(models.Model):
    judul = models.CharField(max_length=100, blank=True)
    foto = models.ImageField(upload_to="galeri/")
    tampil = models.BooleanField(default=True)
    tanggal_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-tanggal_upload"]
        verbose_name = "Foto Galeri"
        verbose_name_plural = "Foto Galeri"

    def __str__(self):
        return self.judul or f"Foto {self.id}"