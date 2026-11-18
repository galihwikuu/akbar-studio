import logging
from datetime import date, datetime, time, timedelta
from collections import defaultdict
from urllib.parse import quote, quote_plus

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse, request
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BookingForm, RatingForm
from .models import TENTANG_DEFAULT, Booking, PengaturanSitus, Rating, FotoGaleri, buat_token
from .services.email import kirim_notif_booking

logger = logging.getLogger(__name__)

def buat_booking(request):
    form = BookingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        request.session["booking_data"] = {
            "nama": data["nama"],
            "whatsapp": data["whatsapp"],
            "tanggal": data["tanggal"].isoformat(),
            "durasi": data["durasi"],
            "jam_mulai": data["jam_mulai"],
        }
        return redirect("konfirmasi_booking")

    tanggal_awal = request.POST.get("tanggal") or timezone.localdate().strftime("%d-%m-%Y")
    daftar_rating = Rating.objects.filter(tampil=True)
    daftar_foto = FotoGaleri.objects.filter(tampil=True)[:4]
    ringkasan = daftar_rating.aggregate(rata=Avg("nilai"), jumlah=Count("id"))
    rata = ringkasan["rata"] or 0
    pengaturan = PengaturanSitus.objects.first()

    now = timezone.localtime()
    jam_sekarang = now.hour
    studio_tutup = jam_sekarang >= settings.JAM_TUTUP
    slot_penuh = False

    if not studio_tutup:
        tanggal_pilih = now.date()
        jam_tersedia = []
        for j in range(settings.JAM_BUKA, settings.JAM_TUTUP):
            if jam_sekarang >= j:
                continue
            jam_tersedia.append(j)
        terisi_hari_ini = Booking.objects.filter(
            tanggal=tanggal_pilih, status="confirmed"
        ).values_list("jam_mulai", flat=True)
        tersedia = [j for j in jam_tersedia if j not in terisi_hari_ini]
        if not tersedia:
            slot_penuh = True

    konteks = {
        "form": form,
        "tanggal_awal": tanggal_awal,
        "alamat": settings.ALAMAT_STUDIO,
        "bintang": range(1, 6),
        "rating_rata": round(rata, 1),
        "rating_bulat": int(rata + 0.5),
        "rating_jumlah": ringkasan["jumlah"],
        "ulasan": daftar_rating.exclude(pesan="").order_by("-created_at")[:10],
        "daftar_foto": daftar_foto,
        "hero_url": pengaturan.foto_hero.url if pengaturan and pengaturan.foto_hero else "",
        "tentang": pengaturan.tentang if pengaturan else TENTANG_DEFAULT,
        "rating_saya": request.session.get("sudah_rating"),
        "embed_maps": f"https://www.google.com/maps?q={quote_plus(settings.ALAMAT_STUDIO)}&output=embed",
        "link_maps": f"https://www.google.com/maps/search/?api=1&query={quote_plus(settings.ALAMAT_STUDIO)}",
        "daftar_durasi": range(1, min(settings.MAKS_DURASI, settings.JAM_TUTUP - settings.JAM_BUKA) + 1),
        "daftar_jam": range(settings.JAM_BUKA, settings.JAM_TUTUP),
        "jam_buka": settings.JAM_BUKA,
        "jam_tutup": settings.JAM_TUTUP,
        "harga": settings.HARGA_PER_JAM,
        "harga_teks": f"{settings.HARGA_PER_JAM:,}".replace(",", "."),
        "hari_ini": timezone.localdate().strftime("%d-%m-%Y"),
        "kontak_wa": f"https://wa.me/{settings.WHATSAPP_ADMIN}",
        "studio_tutup": studio_tutup,
        "slot_penuh": slot_penuh,
        "pesan_studio_tutup": "Studio sudah tutup untuk hari ini. Kami buka kembali besok pagi.",
        "pesan_slot_penuh": "Maaf, semua slot untuk hari ini sudah penuh. Silakan pilih tanggal lain.",
    }
    return render(request, "booking/buat_booking.html", konteks)


def konfirmasi_booking(request):
    data = request.session.get("booking_data")
    if not data:
        return redirect("buat_booking")

    tanggal = date.fromisoformat(data["tanggal"])
    jam_mulai = data["jam_mulai"]
    durasi = data["durasi"]
    rentang = f"{jam_mulai:02d}.00 - {jam_mulai + durasi:02d}.00"
    total = durasi * settings.HARGA_PER_JAM
    total_teks = f"{total:,}".replace(",", ".")

    if request.method == "POST":
        token = buat_token()
        while Booking.objects.filter(token=token).exists():
            token = buat_token()
        try:
            with transaction.atomic():
                daftar = []
                for jam in range(jam_mulai, jam_mulai + durasi):
                    b = Booking.objects.create(
                        nama=data["nama"],
                        whatsapp=data["whatsapp"],
                        tanggal=tanggal,
                        jam_mulai=jam,
                        harga=settings.HARGA_PER_JAM,
                        token=token,
                    )
                    daftar.append(b)
        except IntegrityError:
            messages.error(request, "Jam yang dipilih baru saja diambil orang lain. Coba jam lain.")
            return redirect("buat_booking")
        else:
            try:
                kirim_notif_booking(daftar)
            except Exception as exc:
                logger.exception("Gagal mengirim email notifikasi booking: %s", exc)
                messages.warning(
                    request,
                    "Booking berhasil dibuat, tapi notifikasi email gagal terkirim. Hubungi admin jika diperlukan.",
                )
            del request.session["booking_data"]
            return redirect("booking_sukses", token=token)

    konteks = {
        "nama": data["nama"],
        "whatsapp": data["whatsapp"],
        "tanggal": tanggal,
        "jam_mulai": jam_mulai,
        "durasi": durasi,
        "rentang": rentang,
        "total": total,
        "total_teks": total_teks,
        "harga_per_jam": settings.HARGA_PER_JAM,
        "harga_teks": f"{settings.HARGA_PER_JAM:,}".replace(",", "."),
    }
    return render(request, "booking/konfirmasi_booking.html", konteks)


def booking_sukses(request, token):
    daftar = list(Booking.objects.filter(token=token).order_by("jam_mulai"))
    if not daftar:
        raise Http404
    pertama = daftar[0]
    rentang = f"{pertama.jam_mulai:02d}.00 - {daftar[-1].jam_mulai + 1:02d}.00"
    total = f"{sum(b.harga for b in daftar):,}".replace(",", ".")
    pesan = (
        f"Halo Bapak, saya {pertama.nama} sudah booking studio.\n"
        f"Tanggal: {pertama.tanggal:%d-%m-%Y}\n"
        f"Jam: {rentang}\n"
        f"Total: Rp{total} (bayar di tempat)"
    )
    link_wa = f"https://wa.me/{settings.WHATSAPP_ADMIN}?text={quote(pesan)}"
    return render(
        request,
        "booking/booking_sukses.html",
        {"booking": pertama, "rentang": rentang, "total": total, "token": token, "link_wa": link_wa},
    )


def slot_terisi(request):
    try:
        tanggal = datetime.strptime(request.GET.get("tanggal", ""), "%d-%m-%Y").date()
    except ValueError:
        return JsonResponse({"terisi": [], "semua_terisi": False})
    terisi = Booking.objects.filter(tanggal=tanggal, status="confirmed").values_list("jam_mulai", flat=True)
    terisi_list = list(terisi)
    jam_semua = list(range(settings.JAM_BUKA, settings.JAM_TUTUP))
    semua_terisi = all(j in terisi_list for j in jam_semua)
    return JsonResponse({"terisi": terisi_list, "semua_terisi": semua_terisi})

@require_POST
def beri_rating(request):
    if request.session.get("sudah_rating"):
        messages.error(request, "Kamu sudah memberi rating dari browser ini.")
    else:
        form = RatingForm(request.POST)
        if form.is_valid():
            rating = form.save()
            request.session["sudah_rating"] = rating.nilai
            request.session.set_expiry(60 * 60 * 24 * 365)
            messages.success(request, "Terima kasih, rating kamu tersimpan.")
        else:
            messages.error(request, "Rating belum tersimpan. Isi nama dan pilih 1 sampai 5 bintang.")
    return redirect(f"{reverse('buat_booking')}#rating")

def batal_booking(request):
    context = {}
    if request.method == "POST":
        token = request.POST.get("token", "").strip().upper()
        semua = Booking.objects.filter(token=token).order_by("jam_mulai")
        aktif = [b for b in semua if b.status == "confirmed"]
        if not semua:
            context["error"] = "Token tidak ditemukan."
        elif not aktif:
            context["error"] = "Booking ini sudah dibatalkan."
        elif aktif[-1].sudah_selesai:
            context["error"] = "Booking sudah selesai, tidak dapat dibatalkan."
        elif not aktif[0].bisa_dibatalkan():
            context["error"] = "Booking tidak bisa dibatalkan (batas 1 jam sebelum jam mulai). Hubungi admin."
        else:
            pertama = aktif[0]
            rentang = f"{pertama.jam_mulai:02d}.00 - {aktif[-1].jam_mulai + 1:02d}.00"
            total = f"{sum(b.harga for b in aktif):,}".replace(",", ".")
            context.update({
                "token": token,
                "booking": pertama,
                "rentang": rentang,
                "total": total,
                "batas": pertama.waktu_mulai - timedelta(hours=1),
            })
            
            if request.POST.get("konfirmasi") == "1":
                Booking.objects.filter(token=token, status="confirmed").update(status="cancelled")
                pesan = (
                    f"Halo Bapak, saya {pertama.nama} membatalkan booking.\n"
                    f"Tanggal: {pertama.tanggal:%d-%m-%Y}\n"
                    f"Jam: {rentang}"
                )
                context["dibatalkan"] = True
                context["link_wa"] = f"https://wa.me/{settings.WHATSAPP_ADMIN}?text={quote(pesan)}"
    return render(request, "booking/batal_booking.html", context)


@staff_member_required
def dashboard_pendapatan(request):
    now = timezone.now()

    bookings = Booking.objects.filter(status="confirmed").order_by("tanggal", "jam_mulai")

    token_groups = defaultdict(list)
    for b in bookings:
        token_groups[b.token].append(b)

    finished_bookings = []
    daily_data = defaultdict(int)
    monthly_data = defaultdict(int)

    for token, rows in token_groups.items():
        tanggal = rows[0].tanggal
        jam_mulai_min = min(r.jam_mulai for r in rows)
        jam_mulai_max = max(r.jam_mulai for r in rows)
        jam_selesai = jam_mulai_max + 1
        durasi = len(rows)

        waktu_selesai = timezone.make_aware(datetime.combine(tanggal, time(jam_selesai)))

        if waktu_selesai <= now:
            total = sum(r.harga for r in rows)
            finished_bookings.append({
                "nama": rows[0].nama,
                "tanggal": tanggal,
                "jam_mulai": jam_mulai_min,
                "jam_selesai": jam_selesai,
                "durasi": durasi,
                "total": total,
                "token": token,
            })
            daily_data[tanggal] += total
            monthly_key = f"{tanggal.year}-{tanggal.month:02d}"
            monthly_data[monthly_key] += total

    finished_bookings.sort(key=lambda x: (x["tanggal"], x["jam_mulai"]), reverse=True)

    active_bookings = []
    for token, rows in token_groups.items():
        tanggal = rows[0].tanggal
        jam_mulai_min = min(r.jam_mulai for r in rows)
        jam_mulai_max = max(r.jam_mulai for r in rows)
        jam_selesai = jam_mulai_max + 1
        durasi = len(rows)

        waktu_selesai = timezone.make_aware(datetime.combine(tanggal, time(jam_selesai)))

        if waktu_selesai > now:
            active_bookings.append({
                "nama": rows[0].nama,
                "tanggal": tanggal,
                "jam_mulai": jam_mulai_min,
                "jam_selesai": jam_selesai,
                "durasi": durasi,
                "token": token,
            })

    active_bookings.sort(key=lambda x: (x["tanggal"], x["jam_mulai"]), reverse=True)

    total_pendapatan = sum(b["total"] for b in finished_bookings)
    jumlah_booking = len(finished_bookings)
    rata_rata = total_pendapatan / jumlah_booking if jumlah_booking else 0

    daily_sorted = sorted(daily_data.items())
    monthly_sorted = sorted(monthly_data.items())

    konteks = {
        "total_pendapatan": total_pendapatan,
        "jumlah_booking": jumlah_booking,
        "rata_rata": rata_rata,
        "finished_bookings": finished_bookings[:10],
        "active_bookings": active_bookings[:10],
        "daily_labels": [d.strftime("%d %b") for d, _ in daily_sorted],
        "daily_data": [v for _, v in daily_sorted],
        "monthly_labels": [k for k, _ in monthly_sorted],
        "monthly_data": [v for _, v in monthly_sorted],
    }
    return render(request, "booking/dashboard_pendapatan.html", konteks)


def galeri(request):
    daftar_foto = FotoGaleri.objects.filter(tampil=True)
    konteks = {"daftar_foto": daftar_foto}
    return render(request, "booking/galeri.html", konteks)