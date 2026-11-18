from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from booking.models import Booking


class BookingSelesaiTest(TestCase):
    def setUp(self):
        self.token = "ABCDEFGH"
        self.tanggal_masa_depan = timezone.localdate() + timedelta(days=1)
        self.tanggal_lalu = timezone.localdate() - timedelta(days=1)

    def _buat_booking(self, tanggal, jam_mulai, status="confirmed", token=None):
        if token is None:
            token = self.token
        return Booking.objects.create(
            nama="Tester",
            whatsapp="08123456789",
            tanggal=tanggal,
            jam_mulai=jam_mulai,
            status=status,
            token=token,
        )

    def test_waktu_selesai(self):
        b = self._buat_booking(self.tanggal_masa_depan, 10)
        self.assertEqual(b.waktu_selesai, b.waktu_mulai + timedelta(hours=1))

    def test_sudah_selesai_true_booking_lalu(self):
        b = self._buat_booking(self.tanggal_lalu, 10)
        self.assertTrue(b.sudah_selesai)

    def test_sudah_selesai_false_booking_masa_depan(self):
        b = self._buat_booking(self.tanggal_masa_depan, 10)
        self.assertFalse(b.sudah_selesai)

    def test_bisa_dibatalkan_false_ketika_sudah_selesai(self):
        b = self._buat_booking(self.tanggal_lalu, 10)
        self.assertFalse(b.bisa_dibatalkan())

    def test_batal_booking_error_sudah_selesai(self):
        self._buat_booking(self.tanggal_lalu, 10)
        response = self.client.post(reverse("batal_booking"), {"token": self.token})
        self.assertEqual(response.context["error"], "Booking sudah selesai, tidak dapat dibatalkan.")

    def test_batal_booking_berhasil_ketika_belum_selesai(self):
        self._buat_booking(self.tanggal_masa_depan, 10)
        response = self.client.post(reverse("batal_booking"), {"token": self.token, "konfirmasi": "1"})
        self.assertTrue(response.context.get("dibatalkan"))
        self.assertEqual(Booking.objects.get(token=self.token).status, "cancelled")

    def test_batal_booking_token_tidak_ditemukan(self):
        response = self.client.post(reverse("batal_booking"), {"token": "XXXXXXXX"})
        self.assertEqual(response.context["error"], "Token tidak ditemukan.")

    def test_batal_booking_sudah_dibatalkan(self):
        self._buat_booking(self.tanggal_masa_depan, 10, status="cancelled")
        response = self.client.post(reverse("batal_booking"), {"token": self.token})
        self.assertEqual(response.context["error"], "Booking ini sudah dibatalkan.")


class DashboardActiveBookingTest(TestCase):
    def setUp(self):
        self.user = self.create_superuser("admin", "admin@example.com", "admin123")
        self.client.login(username="admin", password="admin123")
        self.token1 = "TOKEN001"
        self.token2 = "TOKEN002"
        self.tanggal_depan = timezone.localdate() + timedelta(days=1)
        self.tanggal_lalu = timezone.localdate() - timedelta(days=1)

    def create_superuser(self, username, email, password):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_superuser(username, email, password)

    def _buat_booking(self, token, tanggal, jam_mulai, status="confirmed"):
        return Booking.objects.create(
            nama="Tester",
            whatsapp="08123456789",
            tanggal=tanggal,
            jam_mulai=jam_mulai,
            status=status,
            token=token,
        )

    def test_dashboard_tampilkan_active_booking_masa_depan(self):
        self._buat_booking(self.token1, self.tanggal_depan, 10)
        response = self.client.get(reverse("dashboard_pendapatan"))
        self.assertEqual(response.status_code, 200)
        tokens = [b["token"] for b in response.context["active_bookings"]]
        self.assertIn(self.token1, tokens)

    def test_dashboard_tidak_tampilkan_booking_selesai(self):
        self._buat_booking(self.token1, self.tanggal_lalu, 10)
        response = self.client.get(reverse("dashboard_pendapatan"))
        tokens = [b["token"] for b in response.context["active_bookings"]]
        self.assertNotIn(self.token1, tokens)

    def test_dashboard_urutan_terbaru_dulu(self):
        self._buat_booking(self.token1, self.tanggal_depan, 10)
        tanggal_lagi_depan = self.tanggal_depan + timedelta(days=1)
        self._buat_booking(self.token2, tanggal_lagi_depan, 11)
        response = self.client.get(reverse("dashboard_pendapatan"))
        tokens = [b["token"] for b in response.context["active_bookings"]]
        self.assertEqual(tokens[0], self.token2)
        self.assertEqual(tokens[1], self.token1)


class EmailNotifikasiTest(TestCase):
    def setUp(self):
        self.tanggal = timezone.localdate() + timedelta(days=1)
        self.data = {
            "nama": "Tester",
            "whatsapp": "08123456789",
            "tanggal": self.tanggal.strftime("%d-%m-%Y"),
            "durasi": 1,
            "jam_mulai": 10,
        }

    @mock.patch("booking.views.kirim_notif_booking")
    def test_email_terkirim_saat_booking_berhasil(self, mock_kirim):
        # Buat booking dulu untuk menyimpan data ke session
        self.client.post(reverse("buat_booking"), self.data)
        # Konfirmasi booking
        response = self.client.post(reverse("konfirmasi_booking"))
        self.assertEqual(response.status_code, 302)
        mock_kirim.assert_called_once()

        # Verify the email content contains required info
        args = mock_kirim.call_args[0][0]
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].nama, "Tester")
        self.assertEqual(args[0].whatsapp, "08123456789")

    def test_email_tidak_terkirim_saat_booking_gagal(self):
        # Buat booking dulu untuk menyimpan data ke session
        self.client.post(reverse("buat_booking"), self.data)
        # Buat booking lain yang bentrok slot
        Booking.objects.create(
            nama="Orang Lain",
            whatsapp="08987654321",
            tanggal=self.tanggal,
            jam_mulai=10,
            status="confirmed",
            token="EXISTING1",
        )
        response = self.client.post(reverse("konfirmasi_booking"))
        self.assertEqual(response.status_code, 302)
