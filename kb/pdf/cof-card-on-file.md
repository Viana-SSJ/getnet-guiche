---
title: "PowerPoint Presentation"
source: https://site.getnet.com.br/wp-content/uploads/2023/10/COF-Card-On-File.pdf
kind: pdf
fetched: 2026-11-06
---

# PowerPoint Presentation

## Page 1

Classificação da Informação: Interno
COF
Card on file
Válido até dezembro de 2025

## Page 2

COF – CARD ON FILEV1
PLATAFORMA DIGITAL V1
DISPONÍVEL
https://developers.getnet.com.br/api#tag/Pagamento%2Fpaths%2F~1v1~1payments~1credit%2Fpost
Se você estiver usando seu próprio motor de recorrência
ou cofre e precisar enviar o COF, siga estas orientações
para marcá-lo corretamente:
Cofre:
1ª  transação na qual o cartão foi armazenado:
Marcação: ONE_CLICK
Salva-se o Transaction ID dessa transação.
2ª transação na qual esse cartão foi recuperado:
Marcação: ONE_CLICK_PAYMENT
Envia-se o Transaction ID da 1ª transação nas transações subsequentes
a qual esse cartão foi resgatado.
Recorrência:
1ª transação de recorrência, contratação da assinatura:
Marcação: RECURRING
Salva-se o Transaction ID dessa transação.
A partir da 2ª transação da recorrência, motor recuperando dados para
processar as próximas parcelas:
Marcação: RECURRING_PAYMENT
Envia-se o Transaction ID da 1ª transação nas transações subsequentes
de uma recorrência.
Envio do TID Original: O TID pode ser referente a 1ª transação ou de uma transação de verificação de cartão. Esse TID pode ter sido gerado em qualqu er Adq. O envio do TID é recomendado pela bandeira Visa. Para a bandeira Elo o
envio do TID é obrigatório. Para a bandeira Mastercard não é necessário o envio.

## Page 3

COF – CARD ON FILEV2
PLATAFORMA DIGITAL V2
DISPONÍVEL
https://developers.getnet.com.br/idempotency#operation/payment_1
Se você estiver usando seu próprio motor de recorrência
ou cofre e precisar enviar o COF, siga estas orientações
para marcá-lo corretamente:
Cofre:
1ª  transação na qual o cartão foi armazenado:
Marcação: ONE_CLICK
Salva-se o Transaction ID dessa transação.
2ª transação na qual esse cartão foi recuperado:
Marcação: ONE_CLICK_PAYMENT
Envia-se o Transaction ID da 1ª transação nas transações subsequentes
a qual esse cartão foi resgatado.
Recorrência:
1ª transação de recorrência, contratação da assinatura:
Marcação: RECURRING
Salva-se o Transaction ID dessa transação.
A partir da 2ª transação da recorrência, motor recuperando dados para
processar as próximas parcelas:
Marcação: RECURRING_PAYMENT
Envia-se o Transaction ID da 1ª transação nas transações subsequentes
de uma recorrência.
Envio do TID Original: O TID pode ser referente a 1ª transação ou de uma transação de verificação de cartão. Esse TID pode ter sido gerado em qualqu er Adq. O envio do TID é recomendado pela bandeira Visa. Para a bandeira Elo o
envio do TID é obrigatório. Para a bandeira Mastercard não é necessário o envio.

## Page 4

Classificação da Informação: Interno
Se você tiver alguma dúvida, pode entrar em
contato conosco pelos seguintes canais:
