from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from booking.models import Booking


class Command(BaseCommand):
    help = "Tandai booking confirmed yang waktu selesainya telah lewat sebagai cancelled."

    def handle(self, *args, **options):
        now = timezone.now()
        bookings = (
            Booking.objects.filter(status="confirmed")
            .order_by("tanggal", "jam_mulai")
        )
        grouped = defaultdict(list)
        for b in bookings:
            grouped[b.token].append(b)

        jumlah_token = 0
        jumlah_baris = 0
        with transaction.atomic():
            for token, rows in grouped.items():
                terakhir = rows[-1]
                if now >= terakhir.waktu_selesai:
                    jumlah_baris += len(rows)
                    Booking.objects.filter(token=token, status="confirmed").update(
                        status="cancelled"
                    )
                    jumlah_token += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{jumlah_token} token ({jumlah_baris} baris) booking selesai ditandai sebagai cancelled."
            )
        )
