from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('produto/<slug:slug>/', views.produto_detalhe, name='produto_detalhe'),

    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/atualizar/<int:produto_id>/', views.atualizar_carrinho, name='atualizar_carrinho'),
    path('carrinho/remover/<int:produto_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),

    path('checkout/', views.checkout, name='checkout'),
    path('pagamento/<int:pedido_id>/', views.pagamento, name='pagamento'),
    path('pagamento/retorno/', views.pagamento_retorno, name='pagamento_retorno'),
    path('webhook/mercadopago/', views.webhook_mp, name='webhook_mp'),

    path('acompanhar/', views.acompanhar_pedido, name='acompanhar_pedido'),
]
