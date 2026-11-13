import pytest

from agents.getnet.guardrails import mask_sensitive, masked_kinds


@pytest.mark.parametrize("text, kinds, secret", [
    ("Meu cartão é 4111 1111 1111 1111", ["card"], "4111"),
    ("5555-5555-5555-4444", ["card"], "5555"),
    ("Meu CPF é 529.982.247-25", ["cpf"], "529"),
    ("Meu CPF é 529.982.247-25. Obrigado", ["cpf"], "529"),  # a full stop after it
    ("CNPJ: 11.222.333/0001-81.", ["cnpj"], "11.222"),
    ("cpf 52998224725", ["cpf"], "529"),
    ("CNPJ 11.222.333/0001-81", ["cnpj"], "11.222"),
    ("cnpj 11222333000181", ["cnpj"], "11222"),
    ("minha senha é Abc123!", ["password"], "Abc123"),
    ("password: hunter2", ["password"], "hunter2"),
])
def test_sensitive_data_is_masked(text, kinds, secret):
    masked = mask_sensitive(text)
    assert masked_kinds(masked) == kinds
    assert secret not in masked


@pytest.mark.parametrize("text", [
    "Pedido 1234567890123 não chegou",  # 13 digits, fails the Luhn check
    "CPF 529.982.247-24",  # wrong check digit
    "Minha venda de R$ 1.234,56 em 12/11 foi recusada",
    "Ligue 4002-4000 ou 11 98765-4321",
    "A máquina GS-0012345 e a venda T1001",
    "Esqueci minha senha do app",
])
def test_other_numbers_and_words_stay(text):
    assert mask_sensitive(text) == text
