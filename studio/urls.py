from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

def robots_txt(request):
    return HttpResponse(
        "User-agent: *\nAllow: /\n\n"
        "Disallow: /admin/\n\n"
        "Sitemap: https://akbarstudiomusik.web.id/sitemap.xml\n",
        content_type="text/plain",
    )


def sitemap_xml(request):
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>https://akbarstudiomusik.web.id/</loc></url>'
        '<url><loc>https://akbarstudiomusik.web.id/galeri/</loc></url>'
        '</urlset>',
        content_type="application/xml",
    )


urlpatterns = [
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap_xml),
    path("admin/", admin.site.urls),
    path("", include("booking.urls")),

] + [re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}), re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]