"""Popula a loja com os sabores iniciais e cria o acesso ao admin."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from loja.models import Categoria, Produto

User = get_user_model()

# --- Superusuario para o admin ---
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@browniedacasa.com.br', 'brownie123')
    print('  superusuario criado -> usuario: admin | senha: brownie123')
else:
    print('  superusuario admin ja existe')

# --- Categoria ---
cat, _ = Categoria.objects.get_or_create(
    slug='brownies', defaults={'nome': 'Brownies', 'ordem': 1}
)
print('  categoria:', cat.nome)

# --- Os 3 sabores ---
sabores = [
    {
        'nome': 'Brownie Tradicional',
        'slug': 'brownie-tradicional',
        'preco': '12.00',
        'peso_gramas': 90,
        'ordem': 1,
        'destaque': False,
        'descricao': 'O clássico que nunca erra: massa densa de chocolate meio amargo, '
                     'casquinha crocante por fora e úmida por dentro. Feito com chocolate nobre.',
        'ingredientes': 'Chocolate meio amargo, manteiga, ovos, açúcar mascavo, farinha de trigo.',
    },
    {
        'nome': 'Brownie Ninho com Nutella',
        'slug': 'brownie-ninho-com-nutella',
        'preco': '16.00',
        'peso_gramas': 110,
        'ordem': 2,
        'destaque': True,
        'descricao': 'Massa de chocolate recheada com uma camada generosa de creme de leite Ninho '
                     'e um coração de Nutella que escorre no primeiro corte.',
        'ingredientes': 'Chocolate meio amargo, manteiga, ovos, leite Ninho, Nutella, farinha de trigo.',
    },
    {
        'nome': 'Brownie de Brigadeiro',
        'slug': 'brownie-de-brigadeiro',
        'preco': '15.00',
        'peso_gramas': 105,
        'ordem': 3,
        'destaque': False,
        'descricao': 'Nosso brownie coberto com brigadeiro cremoso feito na panela, '
                     'com granulado belga por cima. Para quem gosta de doce de verdade.',
        'ingredientes': 'Chocolate meio amargo, manteiga, ovos, leite condensado, chocolate em pó, granulado belga.',
    },
]

criados = 0
for s in sabores:
    obj, novo = Produto.objects.update_or_create(
        slug=s['slug'],
        defaults={**s, 'categoria': cat, 'disponivel': True},
    )
    criados += 1 if novo else 0
    print('  %-28s R$ %-7s %s' % (obj.nome, obj.preco, '(novo)' if novo else '(atualizado)'))

print()
print('Total de produtos na loja:', Produto.objects.count())
print('Novos criados agora:', criados)
