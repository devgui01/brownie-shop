"""Contexto global dos templates."""

from django.conf import settings

from .carrinho import Carrinho


def carrinho(request):
    """Disponibiliza o carrinho e os dados da loja em toda página."""
    c = Carrinho(request)
    return {
        'carrinho': c,
        'carrinho_quantidade': len(c),
        'carrinho_subtotal': c.subtotal,
        'loja_nome': settings.LOJA_NOME,
        'loja_whatsapp': settings.LOJA_WHATSAPP,
        'loja_email': settings.LOJA_EMAIL,
        'frete_gratis_acima': settings.FRETE_GRATIS_ACIMA,
    }
