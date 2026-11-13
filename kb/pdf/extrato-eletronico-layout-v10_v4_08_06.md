---
title: "EXTRATO-ELETRONICO-LAYOUT-V10_v4_08_06.pdf"
source: https://site.getnet.com.br/wp-content/uploads/2022/04/EXTRATO-ELETRONICO-LAYOUT-V10_v4_08_06.pdf
kind: pdf
fetched: 2026-11-06
---

# EXTRATO-ELETRONICO-LAYOUT-V10_v4_08_06.pdf

## Page 1

Extrato Eletrônico
Layout

A Campanha terá vigência no período compreendido entre às 00h (horário de Brasília) do
dia 01 de janeiro de 2022 a 31 de dezembro de 2022 às 23h59 (horário de Brasília).

## Page 2

SEQ. DESCRIÇÃO               INI. FIM TAM. TIPO COMENTÁRIOS
1 Tipo de Registro 1 1 1 A Fixo = ‘0’
2 Data de criação do arquivo 2 9 8 N Data (DDMMAAAA)
3 Hora de criação do arquivo 10 15 6 N Hora (HHMMSS)
4 Data de referência do Movimento 16 23 8 N Data movimento (DDMMAAAA)
5 Arquivo e Versão 24 31 8 A Fixo = ‘CEADM100’
6 Código do Estabelecimento (loja ou matriz) 32 46 15 A De acordo com o agrupamento no arq.
7 CNPJ do adquirente 47 60 14 N CNPJ do adquirente
8 Nome do adquirente 61 80 20 A Nome do adquirente
9 Sequência 81 89 9 N Número sequencial de remessa
10 Código do adquirente 90 91 2 A Código do adquirente
11 Versão do Layout 92 116 25 A
Para as versões anteriores a V.8.0 serão mantidos os padrões
existentes.
Versão 7.0 - 200 bytes = nome: informação virá em branco
Versão 4.01 = nome: LAYOUT400POSICOES-V4
Versão 8.0 = nome: Sant. v.8.0 400 bytes
Versão 9.0 = nome: Sant. v.9.0 400 bytes
Versão 9.0 = nome: Sant. v.10 400 bytes V
ersão 10.0
= nome: Sant. v.10 400 bytes
12 Reservado para uso futuro 117 400 284 A Espaços
V10 - Tipo 0

## Page 3

SEQ DESCRIÇÃO INI FIM TAM TIPO COMENTÁRIOS
1 Tipo de Registro 1 1 1 A Fixo = ‘1’
2 Código do estabelecimento comercial 2 16 15 A Código de Origem ou maquineta
3 Código do Produto 17 18 2 A Produto (Tabela I)
4 Forma de Captura 19 21 3 A
TEF, POS, MAN(manual), INT(internet), IAT(IATA),MOB (Superget
Mobile), PAG (Pagamento Recorrente),SUP (Superget);Quando o RV
é composto de diversas transações (CV) com formasde captura
diferentes, este campo será = espaços (brancos).A informação de
forma de captura, neste caso, será populadano campo ‘16’ do layout
de transações (CV).(Obs: Para os domín
5 Número do RV 22 30 9 N Número do Resumo de Vendas
6 Data do RV 31 38 8 N Data processamento (DDMMAAAA)
7
Data do Pagamento do RV Para movimento de
vendas indica a data prevista para pagamento Para
movimento financeiro indica a data efetiva do
pagamento 39 46 8 N Data de crédito (DDMMAAAA)
8 Banco 47 49 3 N Código da Instituição Financeira
9 Agência 50 55 6 N Número da Agência
10 Conta Corrente 56 66 11 N Numero da Conta Corrente
11 Número do CVs Aceitos 67 75 9 N
Quantidade de transações com status igual a ‘Aprovada’ (Obs:Para
os domínios RA e PR, esse campo será preenchido com zeros)
12 Número de CVs Rejeitados 76 84 9 N
Quantidade de transações com status diferente de ‘Aprovada’
(Obs:Para os domínios RA e PR, esse campo será preenchido com
zeros)
13 Valor Bruto 85 96 12 N
Valor Bruto do RV(Observação: Para os domínios RA e PR, constará o
valor bruto da antecipação rejeitada)
14 Valor Líquido 97 108 12 N
Valor Líquido (Bruto – Comissão) Valor líquido da Transação (bruto –
comissão) Se seq. 33 = (+), valor do crédito. Se seq. 33 = (-), valor do
débito.(Observação: Para os domínios RA e PR, constará o valor
líquido da antecipação rejeitada) Regra válida para todos os registros
de liquidação – PG / AC /PR
15 Valor da tarifa 109 120 12 N
Valor da Tarifa (se aplicável) Observação: Para os domínios RA e PR,
esse campo será preenchido com zeros 16 Valor da Taxa de
Desconto 121 132 12 N Valor da Taxa de Desconto (Observação: Para
os domínios RA e PR, esse campo será preenchido com zeros)
16 Valor da Taxa de Desconto 121 132 12 N
Valor da Taxa de Desconto (Observação: Para os domínios RA e PR,
esse campo será preenchido com zeros)
17 Valor Rejeitado 133 144 12 N
Valor Total de transações rejeitadas (Observação: Para os domínios
RA e PR, esse campo será preenchido com zeros)18 Valor Crédito
145 156 12 N Valor que será pago² (Observação: Para os domínios
RA e PR, constará o valor creditado da antecipação rejeitada)
18 Valor Crédito 145 156 12 N
Valor que será pago² (Observação: Para os domínios RA e PR,
constará o valor creditado da antecipação rejeitada)
19 Valor Encargos 157 168 12 N
Valor de encargos (Ex.: despesas com antecipação) (Observação:
Para os domínios RA e PR, esse campo será preenchido com zeros)
20 Indicador de tipo de pagamento 169 170 2 A
Preencher com:
‘PF’ – Previsão de Pagamento Futuro
‘PG’ – Pagamento Normal
‘AC’ – Antecipação de Crédito
‘RA’ – Rejeição de Antecipação
‘PR’ – Pagamento da Antecipação Rejeitada
´PD´ - Pagamento Pendente
´CI´ - Cobrança Interna
'CS' - Cessão de crédito
21 Número da parcela do RV 171 172 2 N
Preencher com o número da parcela RV (Observação: Para os
domínios RA e PR, esse campo será preenchido com zeros) Para
transações à vista, número da parcela = 01
22 Quantidade de parcelas do RV 173 174 2 N
Preencher com a quantidade total de parcelas do plano parcelado
(Observação: Para os domínios RA e PR, esse campo será preenchido
com zeros) Para transações à vista, número total de parcelas = 01
23
Código do estabelecimento comercial
Centralizador dos Pagamentos 175 189 15 A Código do centralizador de pagamento ou da Origem
24 Número da Operação de Antecipação 190 204 15 N
Quando efetuado antecipação de recebíveis, será demonstrado no
status AC, no registro tipo 1 o mesmo número da antecipação
apresentado no registro tipo 4, criando o vínculo da operação.
Quando o RV demonstrar a recomposição da agenda após uma
rejeição de Antecipação, Status RA, este campo informa o número
da operação de antecipação rejeitada.
25 Data do vencimento original do RV antecipado 205 212 8 N
Data do vencimento original do Resumo de Venda
Antecipado(DDMMAAAA) Para status (tipo de pagamento) = AC
26 Custo da Operação 213 224 12 N Custo unitário da taxa por vencimento
27 Valor líquido do RV Antecipado 225 236 12 N
Quando efetuada antecipação do RV este campo será preenchido
com o valor líquido (valor do RV – ajustes)
28 Número de controle operação cobrança 237 254 18 N Informação interna do sistema de processamento do adquirente
29
Valor líquido cobrança (Aluguel de POS ou ajuste
de serviços) 255 266 12 N
Neste campo é informado o valor líquido do aluguel do POS ou
ajuste de produtos verticais quando status (tipo de pagamento) = CI
30 ID compensação 267 281 15 N
Código que marcará todos os RV´s e ajustes que fizeram parte da
compensação
31 Moeda 282 284 3 N
Campo demonstra o tipo de moeda da transação. Código 986 moeda
real Código 840 moeda dólar
32
Identificador de baixa da cobrança de serviço
externa (fora da agenda financeira) 285 285 1 A
Identificador = X Marcação para identificação da cobrança interna
de serviços (fora do net na agenda). Quando a compensação ocorrer
na agenda financeira, estará com o conteúdo em branco.
Relacionamento com o código CI e o retorno do débito baixado
como PG. Para as situações de cobrança de serviços verticais, não
haverá apresentação desse identificador.
33 Sinal da transação e/ou ajuste. 286 286 1 N
Quando sinal (+) crédito. Quando sinal (-) débito Os sinais fazem
referência ao valor líquido do resumo - sequência 14 do registro tipo
1.
34 Metadado 1 287 288 2 A
Tipo de conta para pagamento ou Conta Corrente
CC - Conta Corrente
      ==>  Para esse dominio, o valor da conta está na sequencia 10
PP - Conta Poupança
      ==>  Para esse dominio, o valor da conta está na sequencia 35
PG - Conta Pagamento
      ==>  Para esse dominio, o valor da conta está na sequencia 35
CD - Conta Depósito
      ==>  Para esse dominio, o valor da conta está na sequencia 35
CS - Conta Super
      ==>  Para esse dominio, o valor da conta está na sequencia 35
35 Conta para pagamento 289 308 20 N Conta para pagamento
36 Reservado para uso futuro 309 400 92 A Espaços
V10 - Tipo 1

## Page 4

SEQ DESCRIÇÃO INI FIM TAM TIPO COMENTÁRIOS
1 Tipo de Registro 1 1 1 A Fixo = ‘2’
2 Código do estabelecimento comercial 2 16 15 A Código de Origem ou maquineta
3 Número do RV 17 25 9 N Número do Resumo de Vendas
4 NSU do adquirente (Número do CV) 26 37 12 N NSU do adquirente
5 Data da Transação 38 45 8 N Data host (DDMMAAAA)
6 Hora da Transação 46 51 6 N Hora host (HHMMSS)
7 Número do Cartão 52 70 19 A
Número do cartão mascarado. Os dígitos centrais do
número do cartão serão preenchidos com *
8 Valor da Transação 71 82 12 N
Valor da Transação. Se campo 22 = (+), valor do crédito. Se
campo 22 = (-), valor do débito. Para parcelado informa o
valor da parcela
9 Valor do Saque 83 94 12 N Valor do Saque (zeros)
10 Valor da Taxa de Embarque 95 106 12 N Valor da Taxa de Embarque
11 Número de Parcelas 107 108 2 N
Número total de parcelas. Para transações à vista, número
total de parcelas = 01
12
Número da Parcela relacionada ao CV. Para o
movimento de vendas, informa o número da parcela
relacionada a este CV (transação). Para o movimento
financeiro, informa o número da Parcela que está sendo
liberada para pagamento. 109 110 2 N
Número da parcela. Para transações à vista, número da
parcela = 01
13
Valor da Parcela. Para o movimento de vendas, informa
o v
alor da parcela relacionada a este CV (transação).
Para o movimento financeiro, informa o valor da
Parcela que está sendo  liberada para pagamento. 111 122 12 N
Valor da parcela para transações à vista, valor informa o
valor da transação
14
Data do Pagamento. Para o movimento de vendas
indica a Data de previsão de liberação para pagamento
ao estabelecimento comercial. Para o movimento
financeiro indica a data efetiva do pagamento 123 130 8 N Data do pagamento (DDMMAAAA)
15 Código de Autorização 131 140 10 A Código fornecido pelo adquirente
16 Forma de captura 141 143 3 A
TEF, POS, MAN(manual), INT(internet), IAT(IATA), MOB
(Superget Mobile), PAG (Pagamento Recorrente), SUP
(Superget);Se o RV é composto por CVs com forma de
captura iguais, este campo será informado com espaços
(brancos). A informação de forma de captura nestes casos
será populada no campo ‘04’ do lay-out tipo de registro 1 -
resumo de vendas
17 Status da Transação 144 144 1 A Status da transação (Tabela III)
18
 Código do estabelecimento comercial Centralizador
dos Pagamentos 145 159 15 A Código do centralizador de pagamento ou da Origem
19 Código do terminal 160 167 8 A Número do terminal que capturou a transação
20 Moeda 168 170 3 N
Campo demonstra o tipo de moeda da transação. Código
986 moeda real Código 840 moeda dólar
21 Origem do Emissor do Cartão 171 171 1 A N = Cartão emitido no Brasil E = Cartão emitido no Exterior
22 Sinal da transação. 172 172 1 N
Quando sinal (+) crédito. Quando sinal (-) débito Os sinais
fazem referência ao valor da transação - sequência 08 do
registro tipo 2.
23 Carteira Digital 173 175 3 A Carteira Digital (Tabela IV)
24 Valor Comissão da venda 176 187 12 N Valor Comissão do comprovante de venda (MDR)
25 Identificador de tipo do próximo conteudo 188 189 2 A
Metadado com identificador de tipo do próximo
conteúdo:
   01 - Recorrência
   02 - eCommerce
   03 - Recorrência + eCommerce
   04 - Soft Descriptor
26 Conteúdo dinâmico 190 307 118 A
Metadados (sugestão):
01 - Recorrencia:
   De 190 a 225 --> ORDER_ID
   De 226 a 261 --> CHARGE_ID
   De 262 a 264 --> Numero de cobrança recorrente
   De 265 a 307 --> Brancos
02 - eCommerce:
   De 190 a 231 --> TID
   De 232 a 267  --> ORDER_ID
   De 268 a 307 --> Brancos
03 - Recorrencia + TID:
   De 190 a 225 --> ORDER_ID
   De 226 a 261 --> CHARGE_ID
   De 262 a 264 --> Numero de cobrança recorrente
   De 265 a 306 --> TID
   De 307 a 307 --> Brancos
04 - Soft Descriptor
   De 190 a 214 --> Soft Descriptor
27 Identificador de tipo do próximo conteudo 308 309 2 A
Metadado com identificador de tipo do próximo conteúdo:
01 - Info Adicional
28 Conteúdo dinâmico 310 359 50 A Informações adicionais (eCommerce)
29 Reservado para o futuro 360 400 41 A Espaços
231 36
V10 - Tipo 2

## Page 5

SEQ DESCRIÇÃO INI FIM TAM TIPO COMENTÁRIOS
1 Tipo de Registro 1 1 1 A Fixo = ‘3’
2 Código do estabelecimento comercial 2 16 15 A Código de Origem ou maquineta
3 Número do RV ajustado 17 25 9 N RV onde será incluído o ajuste
4 Data do RV 26 33 8 N Preencher com a ‘Data do RV que se deseja ajustar
5 Data do Pagamento do RV 34 41 8 N Data de crédito (DDMMAAAA)
6 Identificador do ajuste 42 61 20 N
Número de documento, número de protocolo de cancelamento ou qualquer
informação que identifique exclusivamente o ajuste no RV.
7 Brancos 62 62 1 A Preenchido com brancos
8 Sinal do valor do ajuste 63 63 1 A + (Crédito) ou - (Débito)
9 Valor do ajuste 64 75 12 N Valor. Se campo 8 = +, valor do crédito. Se campo 8 = -, valor do débito.
10 Motivo do ajuste 76 77 2 A Motivo do Ajuste (Tabela II)
11 Data da carta 78 85 8 N Data da carta ou fax de solicitação de cancelamento
12 Número do Cartão 86 104 19 A
Número do cartão mascarado Os dígitos centrais do número do cartão serão
preenchidos com *
13 Número do RV original 105 113 9 N RV ao qual a transação foi submetida
14 NSU do adquirente (Número do CV) 114 125 12 N NSU da transação original (ou zeros)
15 Data da transação original 126 133 8 N Data (DDMMAAAA)
16 Indicador de tipo de pagamento 134 135 2 A
Preencher com: ‘PF’ – Pagamento Futuro (previsão) ‘PG’ – Pagamento Normal
‘AC’ – Antecipação de Crédito
17 Número do Terminal (transação original) 136 143 8 A Número do terminal que capturou a transação
18 Data Pagamento (original) 144 151 8 A Data (DDMMAAAA) do pagamento original
19 Moeda 152 154 3 N
Campo demonstra o tipo de moeda da transação. Código 986 moeda real Código
840 moeda dólar
20 Valor Comissão da venda 155 166 12 N Valor Comissão do comprovante de venda (MDR) cancelado
21 Identificador de tipo do próximo conteudo 167 168 2 A
 Metadado:
   01 - TID     (somente para Cancelamento ou Chargeback)
   02 - TID + Order_Id       (somente para Cancelamento ou Chargeback)
   03 - Descrição de ajuste
22 Conteúdo dinâmico  169 286 118 A
Conteúdo
   01 - TID:
        De 169 a 210
   02 -
 TID + Order_Id:
        De 169 a 210 --> TID
        De 211 a 246 --> Order_Id
   03 - Descrição de ajuste:
        De 169 a 198
23 Reservado para uso futuro 287 400 113 A Espaço
V10 - Tipo 3

## Page 6

SEQ DESCRIÇÃO INI FIM TAM TIPO COMENTÁRIOS
1 Tipo de Registro 1 1 1 A Fixo = ‘4’
2 Código do estabelecimento comercial 2 16 15 A Demonstra o número do cadastro do Cliente
3 Data da Operação 17 24 8 N Data da contratação da operação de Antecipação (DDMMAAAA)
4 Data do Crédito 25 32 8 N Data do pagamento da operação da Antecipação (DDMMAAAA)
5 Número da Operação 33 47 15 N Número da operação de Antecipação
6 Valor Bruto da Antecipação 48 59 12 N
Esse campo contém o valor bruto da operação de antecipação reportado
no arquivo de Formalizadas enviado pelo Banco Santander. Em relação à
operação de antecipação, o conceito dessa informação corresponde à
soma dos valores brutos das transações agrupadas por vencimento
deduzida a taxa de desconto da comissão.
7 Valor da Taxa de Antecipação 60 71 12 N
Esse campo demonstrará o valor da taxa de antecipação descontada do
estabelecimento comercial
8 Valor Líquido da Antecipação 72 83 12 N
Esse campo contém o valor líquido da operação de antecipação
reportado no arquivo de Formalizadas enviado pelo Banco Santander. Em
relação a operação de antecipação, o conceito dessa informação
corresponde a soma dos valores líquidos das transações agrupadas
9  Taxa ao mês da operação (%) 84 94 11 N
Taxa referencial ao mês (período de 30 dias) contratada da operação de
Antecipação. (Com 4 inteiros e 7 decimais).
10 Código do estabelecimento comercial Centralizador d 95 9 15 A
Esse campo demonstrará o código do estabelecimento comercial
Centralizador de Pagamentos da Rede ou da origem. O conceito desse
campo é o mesmo utilizado atualmente, no registro tipo 1.
11 Banco do Domicílio Bancário 110 112 3 N
Banco do estabelecimento comercial em que será creditado o valor da
antecipação.
12 Agência do Domicílio Bancário 113 118 6 N
Agência do estabelecimento comercial em que será creditado o valor da
antecipação.
13 Conta Corrente 119 129 11 A Numero da Conta Corrente
14 Canal de Antecipação 130 132 3 A
Canal utilizado pelo estabelecimento comercial para realizar a
antecipação.
Os canais são:
CAC (Central de Atendimento)
IBK (Internet Banking)
POR (Portal Corporativo)
POS (POS)
ANT (Automática)
15 Indicador do Tipo de Pagamento 133 134 2 A
Data Esse campo informa o status atual da operação de antecipação em
relação a liquidação. Para este tipo de registro o valor deste campo é: AC
(Antecipação): Esse status deverá ser utilizado para demonstrar as
operações antecipadas;
16 Metadado 1 135 136 2 A
CC - Conta Corrente
      ==>  Para esse dominio, o valor da conta está na sequencia 13
PP - Conta Poupança
      ==>  Para esse dominio, o valor da conta está na sequencia 17
PG - Conta Pagamento
      ==>  Para esse dominio, o valor da conta está na sequencia 17
CD - Conta Depósito
      ==>  Para esse dominio, o valor da conta está na sequencia 17
CS - Conta Super
      ==>  Para esse dominio, o valor da conta está na sequencia 17
17 Conta para pagamento 137 156 20 N
Conta do estabelecimento comercial em que será creditado o valor da
antecipação.
18 Reservado para uso futuro 157 400 244 A Espaços
V10 - Tipo 4

## Page 7

SEQ DESCRIÇÃO INI FIM TAM TIPO COMENTÁRIOS
1 Tipo de registro 1 1 1 A    Fixo “5”.
2 Código do estabelecimento             2 16 15 A    Demonstra o número do cadastro do cliente.
3 Data da operação 17 24 8 N   Data da contratação da operação (DDMMAAAA).
4 Data do crédito da operação           25 32 8 N   Data do pagamento da operação (DDMMAAAA).
5 Número da operação 33 52 20 A   Número da operação.
6 Tipo da operação 53 54 2 A    Modalidade da operação.
  CS – Cessão.
  GV – Gravame.
  CF – Cessão fumaça.
 PG - Pagamento
7 Valor bruto total da operação         55 66 12 N   Valor bruto total da operação. (Adquirência mais Split).
8 Valor bruto da operação – Adquirência 67 78 12 N   Valor bruto da operação – Adquirência.
9 Valor do custo da operação            79 90 12 N   Valor do custo da operação.
10 Valor líquido da operação             91 102 12 N   Valor líquido da operação.
11 Taxa mensal da operação (%)           103 113 11 N   Taxa mensal da operação (%), com 4 inteiros e 7 decimais.
12 Tipo de conta do estabelecimento      114 115 2 A    Tipo da conta do estabelecimento.
 CC – Conta Corrente.
 PP – Conta Poupança.
 PG – Conta Pagamento.
 CD – Conta Depósito.
 CS – Conta Super.
13 Banco do domicílio bancário           116 118 3  N   Banco do domicílio bancário.
14 Agência do domicílio bancário         119 124 6  N   Agência do domicílio bancário.
15 Conta do domicílio bancário           125 144 20 A    Conta do domicílio bancário.
16 Canal de operação 145 147 3  A    Canal por onde a operação foi efetuada.
XXX – xxxxxxxx
17 Tipo de movimento 148 148 1  A    Tipo de movimento.
    I – Inclusão da operação.
    L – Liquidação da operação.
    A – Alteração.
    C – Cancelamento.
18 Tipo de participante 149 151 3  A    Tipo de participante
   IF – Instituição Financeira.
   NIF – Instituição Não Financeira.
19 ID do participante 152 169 18 N   Código do participante na CIP.
20 Tipo de documento do participante     170 170 1 A    Tipo de documento do participante.
   “1” – CNPJ.
   “2” – CPF.
21 CNPJ/CPF do participante              171 184 14 N   CNPJ/CPF do participante.
22 Tipo de conta do participante         185 186 2  A    Tipo da conta do participante.
   CC – Conta Corrente.
   PP – Conta Poupança.
   PG – Conta Pagamento.
   CD – Conta Depósito.
   CS – Conta Super.
23 Banco do participante 187 189 3  N   Banco do participante.
24 Agência do participante               190 195 6  N   Agência do participante.
25 Conta do participante 196 215 20  A    Conta do participante.
26 Código do estabelecimento comercial centraliz 216 230 15 A   Código do centralizador depagamento ou da origem.
27 Reservado para uso futuro             231 400 170 A   Espaços.
V10 - Tipo 5

## Page 8

SEQ DESCRIÇÃO IN I FIM TAM TIPO COMENTÁRIOS
1 Tipo de registro 1 1 1  A      Fixo “6”.
2 Código do estabelecimento          2 16 15 A     Demonstra o número do cadastro do cliente.
3 Data da operação 17 24 8  N    Data da contratação da operação (DDMMAAAA).
4 Número da operação 25 44 20 A    Número da operação.
5 Tipo de operação 45 46 2  A  Modalidade da operação.
   C
S – Cessão.
6 Chave da UR 47 64 18 N   C
have da Unidade de Recebíveis (ID).
7 Código do produto 65 66 2  A  Produto (Tabela I).
8 Data de vencimento da UR           67 74 8  N   Data de vencimento da Unidade de Recebíveis (DDMMAA
9 Valor bruto total da UR            75 86 12 N    Valor bruto total da UR. (Adquirência mais Split).
10 Valor bruto da UR – Adquirência    87 98 12 N    Valor bruto da UR – Adquirência.
11 Valor do custo da UR               99 110 12 N    Valor do custo da UR.
12 Valor líquido da UR                111 122 12 N    Valor líquido da UR.
13 Tipo de conta do estabelecimento   123 124 2  A   Tipo da conta do estabelecimento.
     CC –
 Conta Corrente.
     P
P – Conta Poupança.
     P
G – Conta Pagamento.
     CD
 – Conta Depósito.
     C
S – Conta Super.
14 Banco do domicílio bancário        125 127 3  N  B anco do domicílio bancário.
15 Agência do domicílio bancário      128 133 6  N  Agência do domicílio bancário.
16 Conta do domicílio bancário        134 153 20 A   Conta do domicílio bancário.
17 Tipo de movimento 154 154 1  A  Tipo de movimento.
     I
 – Inclusão da operação.
     L
 – Liquidação da operação.
     A
 – Alteração.
     E –
 Exclusão.
18 Tipo de participante               155 157 3  A  Tipo de participante
     I
F – Instituição Financeira.
     N
IF – Instituição Não Financeira.
19 ID do participante 158 172 18 N   Código do participante na CIP.
20 Tipo de documento do participante  173 173 1  A  Tipo de documento do participante.
     “
1” – CNPJ.
     “
2” – CPF.
21  CNPJ/CPF do participante          174 187 14 N   CNPJ/CPF do participante.
22 Tipo de conta do participante      188 189 2  A  Tipo da conta do participante.
    CC –
 Conta Corrente.
    P
P – Conta Poupança.
    P G – Conta Pagamento.
    CD
 – Conta Depósito.
    C
S – Conta Super.
23 Banco do participante              190 192 3  N  Banco do participante.
24 Agência do participante            193 198 6  N  Agência do participante.
25 Conta do participante              199 218 20 A   Conta do participante.
26 Código do estabelecimento comercial centraliz 219 233 15 A    Código do centralizador de pagamento ou da origem.
27 Reservado para uso futuro          234 400 165 A   Espaços.
V10 - Tipo 6

## Page 9

SEQ. DESCRIÇÃO INI FIM TAM. TIPO COMENTÁRIOS
1 Tipo de Registro 1 1 1  A Fixo = ‘9’
2 Quantidade de Registros 2 10 9  N
Quantidade total de registros do arquivo.
Incluindo os registros header e trailer.
3 Reserva para uso futuro 11 400 390  A Espaços
V10 - Tipo 9
