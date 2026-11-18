from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def get_admin_booking_url():
    return "https://akbarstudiomusik.web.id/admin/booking/booking/"


def kirim_notif_booking(daftar_booking):
    if not daftar_booking:
        return False

    pertama = daftar_booking[0]
    rentang = f"{pertama.jam_mulai:02d}.00 - {daftar_booking[-1].jam_mulai + 1:02d}.00"
    total = sum(b.harga for b in daftar_booking)
    total_teks = f"{total:,}".replace(",", ".")

    konteks = {
        "nama": pertama.nama,
        "whatsapp": pertama.whatsapp,
        "tanggal": pertama.tanggal,
        "rentang": rentang,
        "durasi": len(daftar_booking),
        "total_teks": total_teks,
        "admin_url": get_admin_booking_url(),
        "alamat_studio": settings.ALAMAT_STUDIO,
    }

    subject = f"Notifikasi Booking Baru - {pertama.nama} ({pertama.tanggal:%d-%m-%Y})"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [settings.EMAIL_ADMIN]

    text_content = (
        f"Booking baru masuk:\n"
        f"Nama: {pertama.nama}\n"
        f"Nomor: {pertama.whatsapp}\n"
        f"Tanggal: {pertama.tanggal:%d-%m-%Y}\n"
        f"Jam: {rentang}\n"
        f"Durasi: {len(daftar_booking)} jam\n"
        f"Total: Rp{total_teks}\n"
        f"Lihat di dashboard admin: {settings.ALAMAT_STUDIO}"
    )

    html_content = render_to_string("booking/email/notif_booking.html", konteks)

    msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True
