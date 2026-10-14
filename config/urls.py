from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('loja.urls')),
]

# Media (fotos dos produtos).
# Em produção com DEBUG=False o helper static() não registra a rota,
# então servimos explicitamente — mesma solução do projeto da fábrica.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
