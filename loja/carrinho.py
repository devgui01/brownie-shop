"""Carrinho de compras — guardado na sessão.

Guardar na sessão permite comprar sem criar conta. O carrinho só vira
Pedido no banco quando o cliente vai para o checkout.
"""

from decimal import Decimal

from django.conf import settings

CHAVE_SESSAO = 'carrinho'


class Carrinho:
    def __init__(self, request):
        self.session = request.session
        dados = self.session.get(CHAVE_SESSAO)
        if not dados:
            dados = self.session[CHAVE_SESSAO] = {}
        self.dados = dados

    def adicionar(self, produto, quantidade=1):
        """Soma ao que já existe, respeitando um teto por item."""
        pid = str(produto.id)
        atual = int(self.dados.get(pid, {}).get('quantidade', 0))
        nova = atual + int(quantidade)
        # Teto de 50 unidades por sabor — evita erro de digitação virar pedido gigante
        self.dados[pid] = {
            'quantidade': min(nova, 50),
            'preco': str(produto.preco),
            'nome': produto.nome,
        }
        self.salvar()

    def definir(self, produto_id, quantidade):
        """Define a quantidade exata. Zero remove o item."""
        pid = str(produto_id)
        if pid not in self.dados:
            return
        qtd = int(quantidade)
        if qtd <= 0:
            self.remover(produto_id)
        else:
            self.dados[pid]['quantidade'] = min(qtd, 50)
            self.salvar()

    def remover(self, produto_id):
        pid = str(produto_id)
        if pid in self.dados:
            del self.dados[pid]
            self.salvar()

    def limpar(self):
        self.session[CHAVE_SESSAO] = {}
        self.session.modified = True

    def salvar(self):
        self.session[CHAVE_SESSAO] = self.dados
        self.session.modified = True

    def __iter__(self):
        """Percorre os itens já com subtotal calculado."""
        from .models import Produto
        ids = [int(k) for k in self.dados.keys()]
        produtos = Produto.objects.filter(id__in=ids)
        mapa = {str(p.id): p for p in produtos}

        for pid, item in self.dados.items():
            produto = mapa.get(pid)
            preco = Decimal(item['preco'])
            qtd = item['quantidade']
            yield {
                'produto': produto,
                'produto_id': int(pid),
                'nome': item.get('nome') or (produto.nome if produto else 'Produto removido'),
                'quantidade': qtd,
                'preco': preco,
                'subtotal': preco * qtd,
                'indisponivel': (produto is None or not produto.disponivel),
            }

    def __len__(self):
        return sum(i['quantidade'] for i in self.dados.values())

    @property
    def subtotal(self):
        return sum((i['subtotal'] for i in self), Decimal('0'))

    @property
    def frete(self):
        if not self.dados:
            return Decimal('0')
        if self.subtotal >= Decimal(str(settings.FRETE_GRATIS_ACIMA)):
            return Decimal('0')
        return Decimal(str(settings.FRETE_VALOR))

    @property
    def total(self):
        return self.subtotal + self.frete

    @property
    def falta_para_frete_gratis(self):
        alvo = Decimal(str(settings.FRETE_GRATIS_ACIMA))
        falta = alvo - self.subtotal
        return falta if falta > 0 else Decimal('0')
