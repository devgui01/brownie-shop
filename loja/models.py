"""Modelos da loja de brownies.

Regra de ouro do pagamento: NENHUM dado de cartão é guardado aqui.
Só o ID da transação no gateway, o status e os 4 últimos dígitos
(que o PCI considera dado não sensível).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Categoria(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class Produto(models.Model):
    """Um sabor de brownie."""

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name='produtos',
        null=True, blank=True,
    )
    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    descricao = models.TextField(
        blank=True,
        help_text='Aparece no card do produto. Descreva o sabor.',
    )
    ingredientes = models.TextField(
        blank=True, help_text='Opcional. Lista de ingredientes.',
    )
    preco = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    peso_gramas = models.PositiveIntegerField(
        null=True, blank=True, help_text='Peso aproximado da unidade.',
    )
    foto = models.ImageField(upload_to='produtos/', blank=True, null=True)
    disponivel = models.BooleanField(
        default=True, help_text='Desmarque para esconder da loja.',
    )
    destaque = models.BooleanField(default=False, help_text='Mostra na home.')
    ordem = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return f'{self.nome} (R$ {self.preco})'

    def get_absolute_url(self):
        return reverse('produto_detalhe', kwargs={'slug': self.slug})


class Pedido(models.Model):
    """Pedido do cliente."""

    STATUS = [
        ('carrinho',   'Carrinho'),
        ('aguardando', 'Aguardando pagamento'),
        ('pago',       'Pago'),
        ('preparando', 'Em preparo'),
        ('enviado',    'Saiu para entrega'),
        ('entregue',   'Entregue'),
        ('cancelado',  'Cancelado'),
    ]

    # Cliente pode comprar sem criar conta (convidado)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos',
    )
    status = models.CharField(max_length=12, choices=STATUS, default='carrinho')

    # Dados de entrega
    nome = models.CharField(max_length=120, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    cep = models.CharField(max_length=9, blank=True)
    endereco = models.CharField(max_length=200, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    observacao = models.TextField(blank=True)

    # Valores
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    pago_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Pedido #{self.pk} — {self.get_status_display()}'

    def recalcular(self, salvar=True):
        """Recalcula subtotal, frete e total a partir dos itens."""
        self.subtotal = sum((i.subtotal for i in self.itens.all()), Decimal('0'))
        if self.subtotal >= Decimal(str(settings.FRETE_GRATIS_ACIMA)):
            self.frete = Decimal('0')
        else:
            self.frete = Decimal(str(settings.FRETE_VALOR))
        self.total = self.subtotal + self.frete
        if salvar:
            self.save(update_fields=['subtotal', 'frete', 'total'])
        return self.total

    @property
    def quantidade_itens(self):
        return sum(i.quantidade for i in self.itens.all())


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    # Guarda o preço do momento da compra: se o preço mudar depois, o pedido não muda
    preco_unit = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = 'Item do pedido'
        verbose_name_plural = 'Itens do pedido'

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome}'

    @property
    def subtotal(self):
        return self.preco_unit * self.quantidade


class Pagamento(models.Model):
    """Registro do pagamento no gateway.

    NUNCA guarda número de cartão, validade ou CVV.
    """

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='pagamentos')
    gateway = models.CharField(max_length=20, default='mercadopago')
    gateway_id = models.CharField(max_length=64, unique=True)
    metodo = models.CharField(max_length=30, blank=True)   # credit_card | pix | ticket
    status = models.CharField(max_length=30, blank=True)   # approved | pending | rejected
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cartao_final = models.CharField(max_length=4, blank=True)      # não sensível
    cartao_bandeira = models.CharField(max_length=30, blank=True)  # não sensível
    payload = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.gateway} #{self.gateway_id} — {self.status}'


class EventoWebhook(models.Model):
    """Log de webhooks recebidos. Ajuda a depurar pagamento que não confirmou.

    Guarda só o essencial — não o payload cru com dado sensível.
    """

    gateway = models.CharField(max_length=20, default='mercadopago')
    gateway_id = models.CharField(max_length=64, blank=True)
    assinatura_ok = models.BooleanField(default=False)
    status_recebido = models.CharField(max_length=30, blank=True)
    mensagem = models.CharField(max_length=200, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento de webhook'
        verbose_name_plural = 'Eventos de webhook'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.gateway} {self.gateway_id} ({self.criado_em:%d/%m %H:%M})'
