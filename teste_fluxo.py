"""Teste do fluxo completo: catalogo -> carrinho -> checkout."""
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from loja.models import Pedido, Produto

c = Client()
falhas = []

def check(nome, cond, extra=''):
    print(('  OK    ' if cond else '  FALHOU') + ' ' + nome + (' ' + extra if extra else ''))
    if not cond:
        falhas.append(nome)

print('=== 1. CATALOGO ===')
r = c.get('/')
check('home responde 200', r.status_code == 200, '(status %s)' % r.status_code)
html = r.content.decode()
for nome in ['Brownie Tradicional', 'Ninho com Nutella', 'Brigadeiro']:
    check('sabor visivel: ' + nome, nome in html)

r = c.get('/catalogo/')
check('catalogo responde 200', r.status_code == 200)

p1 = Produto.objects.get(slug='brownie-tradicional')
r = c.get('/produto/%s/' % p1.slug)
check('pagina do produto 200', r.status_code == 200)
check('mostra o preco', '12' in r.content.decode())

print()
print('=== 2. CARRINHO ===')
r = c.get('/carrinho/')
check('carrinho vazio responde 200', r.status_code == 200)
check('avisa que esta vazio', 'vazio' in r.content.decode().lower())

# Adiciona 2 tradicionais
r = c.post('/carrinho/adicionar/%d/' % p1.id, {'quantidade': 2})
check('adicionar redireciona', r.status_code == 302, '(status %s)' % r.status_code)

# Adiciona 1 ninho com nutella
p2 = Produto.objects.get(slug='brownie-ninho-com-nutella')
c.post('/carrinho/adicionar/%d/' % p2.id, {'quantidade': 1})

r = c.get('/carrinho/')
html = r.content.decode()
check('carrinho mostra 2 itens', html.count('item-info') >= 2)
check('mostra Brownie Tradicional', 'Brownie Tradicional' in html)
check('mostra Ninho com Nutella', 'Ninho com Nutella' in html)

# 2x12 + 1x16 = 40 -> frete 10 -> total 50
check('subtotal 40.00', '40' in html)
check('total 50.00', '50' in html)
check('frete cobrado (abaixo do gratis)', 'Grátis' not in html or 'Faltam' in html)

print()
print('=== 3. AJAX (adicionar sem recarregar) ===')
r = c.post('/carrinho/adicionar/%d/' % p1.id, {'quantidade': 1},
           HTTP_X_REQUESTED_WITH='XMLHttpRequest')
check('retorna JSON', r.status_code == 200 and 'application/json' in r['Content-Type'])
import json
d = json.loads(r.content)
check('JSON tem ok=True', d.get('ok') is True)
check('JSON informa quantidade', d.get('quantidade') == 4, '(qtd=%s)' % d.get('quantidade'))

print()
print('=== 4. CHECKOUT ===')
r = c.get('/checkout/')
check('checkout responde 200', r.status_code == 200)
check('tem campo de CEP', 'name="cep"' in r.content.decode())

dados = {
    'nome': 'Maria Teste', 'telefone': '(65) 99999-1234', 'email': 'maria@teste.com',
    'cep': '78000-000', 'endereco': 'Rua das Flores', 'numero': '123',
    'bairro': 'Centro', 'cidade': 'Cuiabá', 'complemento': 'Apto 2',
    'observacao': 'Entregar à tarde',
}
r = c.post('/checkout/', dados)
check('checkout redireciona para pagamento', r.status_code == 302,
      '(status %s -> %s)' % (r.status_code, r.get('Location', '')))

pedido = Pedido.objects.order_by('-id').first()
check('pedido criado no banco', pedido is not None)
if pedido:
    print('      pedido #%d | itens: %d | subtotal R$ %s | frete R$ %s | total R$ %s' % (
        pedido.pk, pedido.itens.count(), pedido.subtotal, pedido.frete, pedido.total))
    check('4 itens no pedido', pedido.itens.count() == 2)
    check('total calculado', str(pedido.total) == '62.00', '(total=%s)' % pedido.total)
    check('subtotal correto', str(pedido.subtotal) == '52.00', '(subtotal=%s)' % pedido.subtotal)
    check('status aguardando', pedido.status == 'aguardando')

print()
print('=== 5. CARRINHO LIMPO APOS CHECKOUT ===')
r = c.get('/carrinho/')
check('carrinho esvaziou', 'vazio' in r.content.decode().lower())

print()
print('=== 6. PAGINA DE PAGAMENTO (sem gateway configurado) ===')
if pedido:
    r = c.get('/pagamento/%d/' % pedido.pk)
    check('pagina responde 200', r.status_code == 200)
    check('avisa que falta configurar', 'não configurado' in r.content.decode().lower()
          or 'indisponível' in r.content.decode().lower())

print()
print('=== 7. ACOMPANHAR PEDIDO ===')
r = c.post('/acompanhar/', {'numero': str(pedido.pk), 'telefone': '999991234'})
check('acompanhar encontra o pedido', r.status_code == 200 and 'Maria Teste' in r.content.decode())

print()
print('=== 8. WEBHOOK SEM ASSINATURA (deve recusar) ===')
r = c.post('/webhook/mercadopago/', data='{"data":{"id":"123"}}',
           content_type='application/json')
check('webhook recusa sem assinatura (401)', r.status_code == 401, '(status %s)' % r.status_code)

print()
print('=' * 60)
if falhas:
    print('FALHAS (%d): %s' % (len(falhas), ', '.join(falhas)))
else:
    print('TODOS OS TESTES PASSARAM')
