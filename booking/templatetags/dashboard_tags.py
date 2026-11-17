from collections import defaultdict
from datetime import datetime, time, date

from django import template
from django.utils import timezone

from ..models import Booking

register = template.Library()


@register.inclusion_tag("booking/dashboard_stats_widget.html", takes_context=True)
def dashboard_stats(context):
    request = context.get("request")
    now = timezone.now()

    selected_date = None
    if request:
        selected_date_str = request.GET.get("tanggal")
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, "%d-%m-%Y").date()
            except ValueError:
                selected_date = timezone.localdate()
        else:
            selected_date = timezone.localdate()

    bookings = Booking.objects.filter(status="confirmed").order_by("tanggal", "jam_mulai")

    token_groups = defaultdict(list)
    for b in bookings:
        token_groups[b.token].append(b)

    finished_bookings = []

    for token, rows in token_groups.items():
        tanggal = rows[0].tanggal
        jam_mulai_min = min(r.jam_mulai for r in rows)
        jam_mulai_max = max(r.jam_mulai for r in rows)
        jam_selesai = jam_mulai_max + 1
        durasi = len(rows)

        waktu_selesai = timezone.make_aware(datetime.combine(tanggal, time(jam_selesai)))

        if waktu_selesai <= now:
            if selected_date and tanggal != selected_date:
                continue
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

    finished_bookings.sort(key=lambda x: (x["tanggal"], x["jam_mulai"]), reverse=True)

    total_pendapatan = sum(b["total"] for b in finished_bookings)
    jumlah_booking = len(finished_bookings)
    rata_rata = total_pendapatan / jumlah_booking if jumlah_booking else 0

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

    return {
        "request": request,
        "selected_date": selected_date,
        "selected_date_str": selected_date.strftime("%d-%m-%Y") if selected_date else "",
        "total_pendapatan": total_pendapatan,
        "jumlah_booking": jumlah_booking,
        "rata_rata": rata_rata,
        "finished_bookings": finished_bookings,
        "active_bookings": active_bookings[:10],
    }
