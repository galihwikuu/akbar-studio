from django.urls import path

from . import views

urlpatterns = [
    path("", views.buat_booking, name="buat_booking"),
    path("konfirmasi/", views.konfirmasi_booking, name="konfirmasi_booking"),
    path("sukses/<str:token>/", views.booking_sukses, name="booking_sukses"),
    path("slot/", views.slot_terisi, name="slot_terisi"),
    path("rating/", views.beri_rating, name="beri_rating"),
    path("batal/", views.batal_booking, name="batal_booking"),
    path("dashboard-pendapatan/", views.dashboard_pendapatan, name="dashboard_pendapatan"),
    path("galeri/", views.galeri, name="galeri"),
]