<div align="center">

# 🍫 Brownie da Casa

### Loja online de brownies artesanais

**Catálogo, carrinho e pagamento com Pix e cartão — feito em Django.**

<br/>

[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Mercado Pago](https://img.shields.io/badge/Mercado_Pago-00B1EA?style=for-the-badge&logo=mercadopago&logoColor=white)](https://www.mercadopago.com.br/)

</div>

---

## Sobre

Loja online para venda de brownies artesanais. O negócio já vende diariamente pelo iFood; este site é o canal próprio, sem intermediário e sem comissão por pedido.

**Sabores disponíveis:**

| Sabor | Descrição |
|---|---|
| **Brownie Tradicional** | Massa densa de chocolate meio amargo, casquinha crocante e interior úmido |
| **Brownie Ninho com Nutella** | Recheado com creme de leite Ninho e coração de Nutella |
| **Brownie de Brigadeiro** | Coberto com brigadeiro cremoso e granulado belga |

O catálogo é gerenciado pelo Django Admin — adicionar um sabor novo não exige mexer em código.

---

## Funcionalidades

**Loja**
- Catálogo com os sabores, foto, descrição, ingredientes e peso
- Página de detalhe com seletor de quantidade
- **Carrinho na sessão** — compra sem precisar criar conta
- Adicionar ao carrinho **sem recarregar a página** (AJAX, com fallback se o JS falhar)
- Frete grátis acima de um valor configurável, com aviso de quanto falta
- Acompanhamento de pedido por número + telefone

**Pagamento**
- **Mercado Pago** (Pix, cartão de crédito e débito)
- Preferência de pagamento criada no servidor
- **Webhook com validação de assinatura HMAC-SHA256**
- Sincronização de status por consulta à API (não confia no retorno do navegador)
- Tratamento de estorno e chargeback

**Gestão (Django Admin)**
- Cadastro de sabores com prévia da foto
- Lista de pedidos com filtro por status e ações em lote
- Registro de pagamentos e log de webhooks recebidos

---

## Segurança do pagamento

Este projeto **nunca armazena dados de cartão**. Nenhum número, validade ou CVV passa pelo servidor Django — o cliente é redirecionado ao ambiente do Mercado Pago, que é o responsável por capturar e processar esses dados.

Isso mantém a loja no escopo **PCI DSS SAQ A** (auto-declaração simplificada) em vez do SAQ D (auditoria completa). Do cartão, só são guardados os **4 últimos dígitos** e a bandeira, que o PCI considera dados não sensíveis.

**Proteções implementadas:**

| Risco | Mitigação |
|---|---|
| Webhook forjado ("pagamento aprovado" falso) | Validação da assinatura `x-signature` com HMAC-SHA256 e comparação em tempo constante |
| Corpo da notificação adulterado | O status é sempre reconfirmado consultando a API do gateway |
| Perda de pedido pago | Webhook é a fonte de verdade, não o redirect do navegador |
| Reenvio infinito de webhook | Resposta sempre `200`, exceto quando a assinatura é inválida |
| Estorno não tratado | Status `refunded` e `charged_back` atualizam o pedido |

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.14 · Django 5.2 |
| Banco | SQLite (dev) — troca para PostgreSQL com uma linha |
| Pagamento | Mercado Pago (SDK oficial Python) |
| Frontend | Django Templates · CSS próprio · JavaScript vanilla |
| Imagens | Pillow |

Sem framework CSS e sem build de frontend: uma folha de estilo escrita à mão, ~400 linhas, com a identidade da marca (paleta de cacau e dourado, tipografia Fraunces + Inter).

---

## Estrutura

```
brownie-shop/
├── config/                 # Configuração do projeto
│   ├── settings.py         #   segredos lidos do .env
│   └── urls.py
├── loja/
│   ├── models.py           # Produto, Pedido, ItemPedido, Pagamento, EventoWebhook
│   ├── carrinho.py         # Carrinho na sessão
│   ├── views.py            # Catálogo, carrinho, checkout, pagamento, webhook
│   ├── admin.py            # Gestão dos sabores e pedidos
│   ├── urls.py
│   └── contexto.py         # Contador do carrinho em toda página
├── templates/loja/         # home, catálogo, produto, carrinho, checkout, retorno
├── seed.py                 # Cadastra os 3 sabores iniciais
└── teste_fluxo.py          # Teste do fluxo completo
```

---

## Como rodar

```bash
# 1. Ambiente
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 2. Dependências
pip install -r requirements.txt

# 3. Configuração — copie e preencha
cp .env.example .env

# 4. Banco e dados iniciais
python manage.py migrate
python seed.py                   # cria os 3 sabores + usuário admin

# 5. Rodar
python manage.py runserver
```

Acesse **http://localhost:8000** para a loja e **/admin/** para a gestão.

> O `seed.py` cria o acesso `admin` / `brownie123`. **Troque a senha** antes de publicar.

---

## Configurando o pagamento

1. Crie a aplicação em `mercadopago.com.br/developers/panel`
2. Copie as credenciais para o `.env`:

```bash
MP_ACCESS_TOKEN=APP_USR-...
MP_PUBLIC_KEY=APP_USR-...
MP_WEBHOOK_SECRET=...
SITE_URL=https://seudominio.com.br
```

3. No painel do Mercado Pago, configure a URL de notificação:
   `https://seudominio.com.br/webhook/mercadopago/`

**Sem essas credenciais a loja continua funcionando** — o pedido é registrado e a página de pagamento avisa que falta configurar. Nada quebra.

---

## Testes

```bash
python teste_fluxo.py
```

Cobre o caminho completo: catálogo → adicionar ao carrinho → AJAX → checkout → criação do pedido → cálculo de frete → limpeza do carrinho → página de pagamento → acompanhamento → rejeição de webhook sem assinatura.

---

## Próximos passos

- [ ] Cálculo de frete por CEP (hoje é valor fixo)
- [ ] Notificação no WhatsApp a cada pedido pago
- [ ] Painel de pedidos para o dia (lista de produção)
- [ ] Cupom de desconto
- [ ] Área de cliente com histórico

---

<div align="center">
<sub>Feito por <a href="https://github.com/devgui01">Guilherme Kauan Marques</a></sub>
</div>
