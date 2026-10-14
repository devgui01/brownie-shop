"""Views da loja: catálogo, carrinho, checkout e pagamento."""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .carrinho import Carrinho
from .models import EventoWebhook, ItemPedido, Pagamento, Pedido, Produto

log = logging.getLogger(__name__)


# ============================================================
# CATÁLOGO
# ============================================================
def home(request):
    produtos = Produto.objects.filter(disponivel=True)
    return render(request, 'loja/home.html', {
        'produtos': produtos,
        'destaques': produtos.filter(destaque=True),
    })


def catalogo(request):
    produtos = Produto.objects.filter(disponivel=True)
    return render(request, 'loja/catalogo.html', {'produtos': produtos})


def produto_detalhe(request, slug):
    produto = get_object_or_404(Produto, slug=slug, disponivel=True)
    relacionados = Produto.objects.filter(disponivel=True).exclude(pk=produto.pk)[:3]
    return render(request, 'loja/produto.html', {
        'produto': produto,
        'relacionados': relacionados,
    })


# ============================================================
# CARRINHO
# ============================================================
def ver_carrinho(request):
    return render(request, 'loja/carrinho.html')


@require_POST
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id, disponivel=True)
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except (TypeError, ValueError):
        quantidade = 1
    quantidade = max(1, min(quantidade, 50))

    carrinho = Carrinho(request)
    carrinho.adicionar(produto, quantidade)
    messages.success(request, f'{produto.nome} adicionado ao carrinho.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'quantidade': len(carrinho),
            'subtotal': str(carrinho.subtotal),
            'mensagem': f'{produto.nome} adicionado!',
        })
    return redirect('ver_carrinho')


@require_POST
def atualizar_carrinho(request, produto_id):
    carrinho = Carrinho(request)
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except (TypeError, ValueError):
        quantidade = 1
    carrinho.definir(produto_id, quantidade)
    return redirect('ver_carrinho')


@require_POST
def remover_do_carrinho(request, produto_id):
    Carrinho(request).remover(produto_id)
    messages.info(request, 'Item removido do carrinho.')
    return redirect('ver_carrinho')


# ============================================================
# CHECKOUT
# ============================================================
def checkout(request):
    """Dados de entrega. O pagamento em si acontece no gateway."""
    carrinho = Carrinho(request)
    if len(carrinho) == 0:
        messages.warning(request, 'Seu carrinho está vazio.')
        return redirect('catalogo')

    if request.method == 'POST':
        dados = request.POST
        obrigatorios = ['nome', 'telefone', 'cep', 'endereco', 'numero', 'bairro', 'cidade']
        faltando = [c for c in obrigatorios if not dados.get(c, '').strip()]
        if faltando:
            messages.error(request, 'Preencha os campos obrigatórios: ' + ', '.join(faltando))
            return render(request, 'loja/checkout.html', {'valores': dados})

        pedido = Pedido.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            status='aguardando',
            nome=dados.get('nome', '').strip(),
            telefone=dados.get('telefone', '').strip(),
            email=dados.get('email', '').strip(),
            cep=dados.get('cep', '').strip(),
            endereco=dados.get('endereco', '').strip(),
            numero=dados.get('numero', '').strip(),
            complemento=dados.get('complemento', '').strip(),
            bairro=dados.get('bairro', '').strip(),
            cidade=dados.get('cidade', '').strip(),
            observacao=dados.get('observacao', '').strip(),
        )

        for item in carrinho:
            ItemPedido.objects.create(
                pedido=pedido,
                produto=item['produto'],
                quantidade=item['quantidade'],
                preco_unit=item['preco'],
            )

        pedido.recalcular()
        carrinho.limpar()
        return redirect('pagamento', pedido_id=pedido.pk)

    return render(request, 'loja/checkout.html')


# ============================================================
# PAGAMENTO — Mercado Pago
# ============================================================
def _sdk():
    import mercadopago
    if not settings.MP_ACCESS_TOKEN:
        return None
    return mercadopago.SDK(settings.MP_ACCESS_TOKEN)


def pagamento(request, pedido_id):
    """Cria a preferência de pagamento e manda o cliente pro gateway."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    sdk = _sdk()
    if sdk is None:
        return render(request, 'loja/pagamento_indisponivel.html', {'pedido': pedido})

    preferencia = sdk.preference().create({
        'items': [{
            'title': f'Pedido #{pedido.pk} — {settings.LOJA_NOME}',
            'quantity': 1,
            'unit_price': float(pedido.total),
            'currency_id': 'BRL',
        }],
        'external_reference': str(pedido.pk),
        'back_urls': {
            'success': f'{settings.SITE_URL}{reverse("pagamento_retorno")}',
            'pending': f'{settings.SITE_URL}{reverse("pagamento_retorno")}',
            'failure': f'{settings.SITE_URL}{reverse("pagamento_retorno")}',
        },
        'auto_return': 'approved',
        'notification_url': f'{settings.SITE_URL}{reverse("webhook_mp")}',
        'statement_descriptor': settings.LOJA_NOME[:22].upper(),
        'payment_methods': {
            'installments': 1,        # brownie: sem parcelamento
        },
    })

    if preferencia.get('status') not in (200, 201):
        log.error('Falha ao criar preferencia MP: %s', preferencia)
        messages.error(request, 'Não foi possível iniciar o pagamento. Tente novamente.')
        return redirect('ver_carrinho')

    resp = preferencia['response']
    Pagamento.objects.create(
        pedido=pedido,
        gateway_id=str(resp['id']),
        metodo='preferencia',
        status='pending',
        valor=pedido.total,
        payload={'init_point': resp.get('init_point', '')},
    )

    # init_point: produção | sandbox_init_point: testes
    url = resp.get('init_point') or resp.get('sandbox_init_point')
    return redirect(url)


def pagamento_retorno(request):
    """Volta do gateway. NÃO é fonte de verdade — o webhook é."""
    ref = request.GET.get('external_reference') or request.GET.get('payment_id')
    pedido = None

    if request.GET.get('external_reference'):
        pedido = Pedido.objects.filter(pk=request.GET['external_reference']).first()
    elif request.GET.get('payment_id'):
        pag = Pagamento.objects.filter(gateway_id=request.GET['payment_id']).first()
        pedido = pag.pedido if pag else None

    if pedido:
        # Reconsulta o gateway para não depender do retorno do navegador
        _sincronizar_pagamento(pedido)

    return render(request, 'loja/pagamento_retorno.html', {'pedido': pedido})


# ============================================================
# WEBHOOK — a fonte de verdade do pagamento
# ============================================================
def _assinatura_valida(request) -> bool:
    """Valida o header x-signature (HMAC-SHA256) do Mercado Pago.

    Sem isso, qualquer pessoa pode forjar "pagamento aprovado".
    """
    segredo = settings.MP_WEBHOOK_SECRET
    if not segredo:
        log.warning('MP_WEBHOOK_SECRET não configurado — webhook aceito sem validação')
        return False

    assinatura = request.headers.get('x-signature', '')
    request_id = request.headers.get('x-request-id', '')
    data_id = request.GET.get('data.id', '') or request.GET.get('id', '')
    if not assinatura:
        return False

    partes = dict(p.split('=', 1) for p in assinatura.split(',') if '=' in p)
    ts, v1 = partes.get('ts'), partes.get('v1')
    if not ts or not v1:
        return False

    manifesto = f'id:{data_id};request-id:{request_id};ts:{ts};'
    esperado = hmac.new(
        segredo.encode(), manifesto.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperado, v1)


def _sincronizar_pagamento(pedido):
    """Consulta o gateway e atualiza pedido + pagamento. Idempotente."""
    sdk = _sdk()
    if sdk is None:
        return None

    # Busca o pagamento mais recente deste pedido no gateway
    busca = sdk.payment().search({'external_reference': str(pedido.pk)})
    if busca.get('status') != 200:
        return None

    resultados = busca.get('response', {}).get('results', [])
    if not resultados:
        return None

    info = sorted(resultados, key=lambda r: r.get('date_created', ''))[-1]
    status = info.get('status', '')

    cartao = info.get('card') or {}
    Pagamento.objects.update_or_create(
        gateway_id=str(info['id']),
        defaults={
            'pedido': pedido,
            'metodo': info.get('payment_type_id', ''),
            'status': status,
            'valor': info.get('transaction_amount', 0),
            'cartao_final': cartao.get('last_four_digits', ''),
            'cartao_bandeira': cartao.get('payment_method', {}).get('id', '')
                               if isinstance(cartao.get('payment_method'), dict)
                               else '',
            'payload': {
                'id': info.get('id'),
                'status': status,
                'status_detail': info.get('status_detail'),
                'payment_type_id': info.get('payment_type_id'),
                'date_approved': info.get('date_approved'),
            },
        },
    )

    if status == 'approved' and pedido.status != 'pago':
        pedido.status = 'pago'
        pedido.pago_em = timezone.now()
        pedido.save(update_fields=['status', 'pago_em'])
    elif status in ('refunded', 'charged_back') and pedido.status != 'cancelado':
        pedido.status = 'cancelado'
        pedido.save(update_fields=['status'])

    return status


@csrf_exempt
def webhook_mp(request):
    """Recebe a notificação do Mercado Pago."""
    assinatura_ok = _assinatura_valida(request)

    try:
        corpo = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        corpo = {}

    pagamento_id = (
        corpo.get('data', {}).get('id')
        or request.GET.get('data.id')
        or request.GET.get('id')
    )

    ev = EventoWebhook.objects.create(
        gateway_id=str(pagamento_id or ''),
        assinatura_ok=assinatura_ok,
        status_recebido=corpo.get('action', corpo.get('type', '')),
        mensagem='',
    )

    if not assinatura_ok:
        ev.mensagem = 'Assinatura inválida — descartado'
        ev.save(update_fields=['mensagem'])
        return HttpResponse(status=401)

    if not pagamento_id:
        ev.mensagem = 'Sem id de pagamento'
        ev.save(update_fields=['mensagem'])
        return HttpResponse(status=200)

    # Consulta o gateway: o corpo da notificação é só um aviso
    sdk = _sdk()
    if sdk is None:
        ev.mensagem = 'Gateway não configurado'
        ev.save(update_fields=['mensagem'])
        return HttpResponse(status=200)

    info = sdk.payment().get(pagamento_id).get('response', {})
    pedido_id = info.get('external_reference')

    if not pedido_id:
        ev.mensagem = 'Sem external_reference'
        ev.save(update_fields=['mensagem'])
        return HttpResponse(status=200)

    pedido = Pedido.objects.filter(pk=pedido_id).first()
    if not pedido:
        ev.mensagem = f'Pedido {pedido_id} não encontrado'
        ev.save(update_fields=['mensagem'])
        return HttpResponse(status=200)

    status = _sincronizar_pagamento(pedido)
    ev.mensagem = f'Pedido {pedido.pk} -> {status}'
    ev.save(update_fields=['mensagem'])

    # Sempre 200: senão o Mercado Pago reenvia por horas
    return HttpResponse(status=200)


# ============================================================
# ACOMPANHAMENTO DO PEDIDO
# ============================================================
def acompanhar_pedido(request):
    """Cliente consulta o pedido pelo número + telefone."""
    pedido = None
    erro = None
    if request.method == 'POST':
        numero = request.POST.get('numero', '').strip().lstrip('#')
        telefone = ''.join(c for c in request.POST.get('telefone', '') if c.isdigit())
        if numero and telefone:
            p = Pedido.objects.filter(pk=numero).first() if numero.isdigit() else None
            if p and ''.join(c for c in p.telefone if c.isdigit()).endswith(telefone[-8:]):
                pedido = p
            else:
                erro = 'Pedido não encontrado. Confira o número e o telefone.'
        else:
            erro = 'Informe o número do pedido e o telefone.'
    return render(request, 'loja/acompanhar.html', {'pedido': pedido, 'erro': erro})
