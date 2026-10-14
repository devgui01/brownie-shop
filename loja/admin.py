"""Admin da loja — é aqui que vocês cadastram os brownies e veem os pedidos."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Categoria, EventoWebhook, ItemPedido, Pagamento, Pedido, Produto,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'ordem')
    prepopulated_fields = {'slug': ('nome',)}


class ItemInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ('produto', 'quantidade', 'preco_unit', 'subtotal_show')
    can_delete = False

    @admin.display(description='Subtotal')
    def subtotal_show(self, obj):
        return f'R$ {obj.subtotal:.2f}' if obj.pk else '—'


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    can_delete = False
    fields = ('gateway', 'gateway_id', 'metodo', 'status', 'valor', 'cartao_final', 'criado_em')
    readonly_fields = fields


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('miniatura', 'nome', 'preco', 'peso_gramas', 'disponivel', 'destaque', 'ordem')
    list_editable = ('preco', 'disponivel', 'destaque', 'ordem')
    list_filter = ('disponivel', 'destaque', 'categoria')
    search_fields = ('nome', 'descricao')
    prepopulated_fields = {'slug': ('nome',)}
    fieldsets = (
        ('Identificação', {'fields': ('nome', 'slug', 'categoria', 'ordem')}),
        ('Descrição', {'fields': ('descricao', 'ingredientes')}),
        ('Preço e peso', {'fields': ('preco', 'peso_gramas')}),
        ('Imagem', {'fields': ('foto', 'miniatura_preview')}),
        ('Visibilidade', {'fields': ('disponivel', 'destaque')}),
    )
    readonly_fields = ('miniatura_preview',)

    @admin.display(description='Foto')
    def miniatura(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="height:38px;border-radius:6px"/>', obj.foto.url)
        return '—'

    @admin.display(description='Prévia')
    def miniatura_preview(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="max-height:220px;border-radius:10px"/>', obj.foto.url)
        return 'Sem foto ainda. Envie uma imagem quadrada (ex: 800x800).'


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'telefone', 'status', 'total', 'criado_em', 'pago_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('nome', 'telefone', 'email', 'id')
    date_hierarchy = 'criado_em'
    inlines = [ItemInline, PagamentoInline]
    readonly_fields = ('subtotal', 'frete', 'total', 'criado_em', 'atualizado_em', 'pago_em')
    fieldsets = (
        ('Status', {'fields': ('status', 'usuario', 'pago_em')}),
        ('Cliente', {'fields': ('nome', 'telefone', 'email')}),
        ('Entrega', {'fields': ('cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'observacao')}),
        ('Valores', {'fields': ('subtotal', 'frete', 'total')}),
        ('Datas', {'fields': ('criado_em', 'atualizado_em')}),
    )

    actions = ['marcar_preparando', 'marcar_enviado', 'marcar_entregue']

    @admin.action(description='Marcar como "Em preparo"')
    def marcar_preparando(self, request, queryset):
        n = queryset.filter(status='pago').update(status='preparando')
        self.message_user(request, f'{n} pedido(s) em preparo.')

    @admin.action(description='Marcar como "Saiu para entrega"')
    def marcar_enviado(self, request, queryset):
        n = queryset.update(status='enviado')
        self.message_user(request, f'{n} pedido(s) saíram para entrega.')

    @admin.action(description='Marcar como "Entregue"')
    def marcar_entregue(self, request, queryset):
        n = queryset.update(status='entregue')
        self.message_user(request, f'{n} pedido(s) entregues.')


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('gateway_id', 'pedido', 'metodo', 'status', 'valor', 'cartao_final', 'criado_em')
    list_filter = ('status', 'metodo', 'gateway')
    search_fields = ('gateway_id', 'pedido__id', 'pedido__nome')
    readonly_fields = ('gateway', 'gateway_id', 'metodo', 'status', 'valor',
                       'cartao_final', 'cartao_bandeira', 'payload', 'criado_em', 'atualizado_em')

    def has_add_permission(self, request):
        return False


@admin.register(EventoWebhook)
class EventoWebhookAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'gateway_id', 'assinatura_ok', 'status_recebido', 'mensagem')
    list_filter = ('assinatura_ok',)
    readonly_fields = ('gateway', 'gateway_id', 'assinatura_ok', 'status_recebido', 'mensagem', 'criado_em')

    def has_add_permission(self, request):
        return False


admin.site.site_header = 'Brownie — Administração'
admin.site.site_title = 'Brownie'
admin.site.index_title = 'Gerenciar loja'
