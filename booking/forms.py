from django import forms
from django.conf import settings
from django.utils import timezone

from .models import Booking, Rating


def pilihan_durasi():
    maks = min(settings.MAKS_DURASI, settings.JAM_TUTUP - settings.JAM_BUKA)
    return [(d, f"{d} jam") for d in range(1, maks + 1)]


def pilihan_jam_mulai():
    return [(j, f"{j:02d}.00") for j in range(settings.JAM_BUKA, settings.JAM_TUTUP)]


class BookingForm(forms.Form):
    nama = forms.CharField(max_length=100)
    whatsapp = forms.CharField(max_length=20)
    tanggal = forms.DateField(
        widget=forms.DateInput(attrs={"type": "text", "placeholder": "dd-mm-yyyy", "pattern": "[0-9]{2}-[0-9]{2}-[0-9]{4}"}),
        input_formats=["%d-%m-%Y"],
    )
    durasi = forms.TypedChoiceField(choices=pilihan_durasi, coerce=int)
    jam_mulai = forms.TypedChoiceField(choices=pilihan_jam_mulai, coerce=int)

    def clean_whatsapp(self):
        nomor = "".join(c for c in self.cleaned_data["whatsapp"] if c.isdigit())
        if not (nomor.startswith("08") or nomor.startswith("628")):
            raise forms.ValidationError("Nomor WhatsApp harus diawali 08 atau 628.")
        if not 9 <= len(nomor) <= 15:
            raise forms.ValidationError("Nomor WhatsApp tidak valid.")
        return nomor

    def clean_tanggal(self):
        tanggal = self.cleaned_data["tanggal"]
        if tanggal < timezone.localdate():
            raise forms.ValidationError("Tanggal yang dipilih sudah lewat.")
        return tanggal

    def clean(self):
        data = super().clean()
        tanggal = data.get("tanggal")
        durasi = data.get("durasi")
        mulai = data.get("jam_mulai")
        if tanggal is None or durasi is None or mulai is None:
            return data

        jam_dipesan = list(range(mulai, mulai + durasi))
        if jam_dipesan[-1] >= settings.JAM_TUTUP:
            raise forms.ValidationError("Durasi booking melebihi jam tutup studio.")

        if tanggal == timezone.localdate() and timezone.localtime().hour >= mulai:
            raise forms.ValidationError("Waktu booking untuk jam ini sudah lewat.")

        terisi = Booking.objects.filter(
            tanggal=tanggal, status="confirmed", jam_mulai__in=jam_dipesan
        ).values_list("jam_mulai", flat=True)
        if terisi:
            daftar = ", ".join(f"{j:02d}.00" for j in sorted(terisi))
            raise forms.ValidationError(f"Maaf, jam {daftar} sudah dipilih orang lain.")
        return data

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ["nama", "nilai", "pesan"]