# Dicionário de métricas e regras de negócio — FX Macro Analytics V2

> **Versão documental:** 09/11/2026\
> **Escopo:** contratos SQL, unidades, indicadores do Power BI e critérios de interpretação.\
> **Importante:** valores exemplificados nas tabelas abaixo foram observados nas capturas do dashboard de 09/11/2026. Não substituem uma reconciliação independente das fórmulas DAX com o SQL Server.

## 1. Fontes de dados

| Indicador | SGS | Frequência na ingestão | Unidade recebida | Aplicação |
| --- | ---: | --- | --- | --- |
| IPCA | `433` | Mensal | % no mês | Inflação mensal, acumulado no ano e IPCA 12M |
| USD/BRL | `1` | Diária | R$ por US$ 1 | Câmbio do dólar |
| EUR/BRL | `21619` | Diária | R$ por € 1 | Câmbio do euro |
| SELIC efetiva anualizada | `1178` | Diária | % a.a., base 252 | Política monetária e indicador de juros reais |
| Meta SELIC (Copom) | `432` | Diária | % a.a. | Meta da taxa básica e comparação com a efetiva |

Fontes de referência já documentadas no projeto:
- Metadados BCB: <https://www4.bcb.gov.br/pec/series/port/metadados/mg45p.htm>
- Catálogo da SGS 1178: <https://dadosabertos.bcb.gov.br/dataset/1178-taxa-de-juros---selic-anualizada-base-252>

**Atenção às unidades:** a série 1178 **já está anualizada**; sua média no mês continua expressa em **% a.a.**, não em rendimento mensal. A série 432 também é expressa em **% a.a.**, mas representa a **meta**, não a taxa efetivamente observada. A frequência diária da SGS 432 não significa alteração diária da decisão do Copom.

## 2. Camadas e contratos de dados

| Camada | Objeto | Contrato / uso |
| --- | --- | --- |
| RAW | `data/RAW/<SERIE>.csv`, JSON, `manifest.json`, snapshots | CSVs normalizados com `data`, `valor`, `serie`, `codigo`, `frequencia`; manifest com hash SHA-256 |
| SILVER | `dbo.fx_macro_indicadores` | Colunas `data`, `indicador`, `frequencia`, `valor`, `fonte`; contém `IPCA`, `SELIC` e `SELIC_META` |
| SILVER | `silver.usd_brl`, `silver.eur_brl` | Observações cambiais diárias |
| GOLD | `dbo.vw_gold_ipca` | IPCA por mês |
| GOLD | `dbo.vw_gold_selic` | Média mensal da SELIC efetiva anualizada (`selic_media`) |
| GOLD | `dbo.vw_gold_macro` | Combinação mensal de IPCA e SELIC efetiva |
| GOLD | `dbo.vw_macro_monthly` | `macro_date`, `ipca_mensal`, `selic_mensal` |
| GOLD | `dbo.vw_gold_selic_meta` | `data`, `selic_meta_aa`: observações diárias da meta SELIC |
| ANALYTICS | `dbo.vw_fx_monthly_summary` | Resumo cambial mensal, incluindo `currency`, `avg_rate`, `min_rate`, `max_rate` |
| ANALYTICS | `dbo.vw_macro_ipca_12m` | `macro_date`, `ipca_mensal`, `ipca_12m` |
| ANALYTICS | `dbo.vw_macro_real_rate` | Indicador composto de juros reais |

**Compatibilidade:** o nome legado `selic_mensal` significa **média da taxa SELIC anualizada observada no mês**. Não deve ser interpretado como rentabilidade mensal nem anualizado novamente.

A view `vw_gold_selic_meta` mantém a granularidade diária. Para o cartão de **mês comum**, a regra descrita no dashboard é utilizar a **última meta disponível no mês de referência**, em conjunto com a **média mensal da SELIC efetiva** e os juros reais desse mesmo mês.

## 3. Definições matemáticas

### 3.1 IPCA acumulado em 12 meses

Para 12 taxas mensais consecutivas `r_i`, recebidas em percentual:

```text
IPCA_12M (%) = 100 × [ ∏(i=1..12) (1 + r_i / 100) − 1 ]
```

- Não usar soma simples das taxas mensais.
- Exigir 12 meses consecutivos para formar uma janela válida.
- Os 11 primeiros meses de uma série sem histórico anterior não têm janela completa.
- A referência central de **3%** e o teto de **4,5%** são exibidos no gráfico de **IPCA 12M**. A aplicabilidade desses parâmetros a períodos históricos diferentes deve respeitar a vigência das metas.

### 3.2 IPCA acumulado no ano

```text
IPCA_YTD (%) = 100 × [ ∏(meses de janeiro até o mês de referência) (1 + r_m / 100) − 1 ]
```

O IPCA acumulado no ano descreve a inflação desde janeiro; **não é a mesma métrica** usada para confrontar o IPCA 12M com a meta e o teto.

### 3.3 SELIC efetiva anualizada

```text
SELIC_efetiva_mensal (% a.a.) = média das observações SGS 1178 no mês
```

A média preserva a unidade **% a.a.**. Não aplicar `^12`, multiplicação por 12 nem outra anualização sobre essa série.

### 3.4 Meta SELIC

```text
Meta_SELIC_mês (% a.a.) = última observação disponível da SGS 432 no mês de referência
```

A medida deve identificar a data válida da série no mês escolhido, e não simplesmente agregar todas as observações pela soma ou pela média. A medida de **último dado disponível** e a medida de **mês comum** têm finalidades diferentes: a primeira informa o valor mais recente da fonte; a segunda permite comparar indicadores com a mesma referência temporal.

### 3.5 Juros reais — indicador ex post de cenário

```text
Juros_reais (%) = 100 × [ (1 + SELIC_efetiva_mensal / 100)
                          / (1 + IPCA_12M / 100) − 1 ]
```

Compara uma taxa nominal anualizada observada com a inflação acumulada **passada** em 12 meses. É um indicador analítico de cenário, **não** a taxa real esperada para o futuro nem o retorno realizado de uma aplicação específica.

### 3.6 Variações e unidades

| Tipo de variação | Cálculo | Unidade exibida |
| --- | --- | --- |
| IPCA 12M, SELIC e juros reais | `valor_atual_em_% − valor_anterior_em_%` | Pontos percentuais (`pp`) |
| Meta SELIC — mês comum | `meta_fim_mês_atual − meta_fim_mês_anterior` | Pontos percentuais (`pp`) |
| Câmbio mês contra mês (MoM) | `100 × (média_mês_atual / média_mês_anterior − 1)` | `%` |
| Distância do IPCA à meta central | `IPCA_12M − 3,00` | Pontos percentuais (`pp`) |

**SQL × DAX:** valores SQL como `13.75` e `4.58` representam `13,75%` e `4,58%`. Para formatar a medida como **Porcentagem** no Power BI, dividir por 100 **uma única vez**. Já uma diferença de `-0.25` entre duas taxas SQL é `-0,25 pp` e **não** deve ser multiplicada por 100 ao ser exibida como texto em pp.

## 4. Câmbio: nível, faixa e amplitude

- `avg_rate`: média das cotações disponíveis no mês. Um cartão que usa a última média mensal **não** representa necessariamente a última cotação diária.
- `min_rate` e `max_rate`: menor e maior cotação observadas no mês.
- Comparação entre USD e EUR: as taxas são expressas em **reais por uma unidade de moeda estrangeira**.
- Variação MoM: deve comparar meses equivalentes da mesma moeda, filtrando `currency` (`USD_BRL` ou `EUR_BRL`).

### Amplitude USD — 12 meses fechados

Conforme a regra descrita no dashboard:

```text
Amplitude_mensal (%) = 100 × (máxima_mensal − mínima_mensal) / média_mensal
Amplitude_USD_12M (%) = média das amplitudes mensais de 12 meses fechados
```

Faixas **internas e exploratórias**:

| Amplitude | Status |
| --- | --- |
| Menor que 2% | Baixa |
| De 2% até 5% | Moderada |
| Maior que 5% | Elevada |

**Amplitude não é volatilidade estatística** de retornos nem desvio-padrão anualizado. A janela de 12 meses fechados pode diferir do intervalo visível no gráfico; ambos devem ter referência explícita.

## 5. Contratos de exibição — Power BI

### Página 01 — Visão Macro

- Cartões: **IPCA 12M**, **Meta SELIC**, **juros reais** e **SELIC efetiva anualizada**.
- Para comparação conjunta, o dashboard passou a usar um **mês comum fechado**. Na captura revisada, a referência indicada é **09/2026**.
- Gráfico misto: **barras de IPCA mensal** e **linha de SELIC efetiva anualizada**. São unidades e escalas diferentes, exibidas em eixos separados.
- O cenário de atenção e os status de juros são **classificações internas do relatório**, não pareceres oficiais do BCB. O rodapé da captura informa cenário de atenção quando a inflação está fora da banda ou quando os juros reais são ≥ 3%; essa regra deve ser conferida na medida DAX antes de ser considerada testada.

### Página 02 — Câmbio

- USD/BRL e EUR/BRL por período; evolução de médias mensais e comparação de mínima, média e máxima.
- Amplitude do USD calculada sobre **12 meses fechados**, com período exibido separadamente.
- Os rótulos das barras usam **R$ por unidade da moeda estrangeira**.

### Página 03 — Inflação

- IPCA 12M versus meta central de 3% e teto de 4,5%.
- Tendência, distância da meta e proporção de meses acima do teto.
- IPCA acumulado no ano em gráfico separado, **sem tratá-lo como critério direto de cumprimento da meta de IPCA 12M**.
- O percentual de meses acima do teto precisa mostrar **numerador e denominador** (por exemplo, `3 de 9 meses`).
- A expressão **“média histórica”** precisa de uma janela histórica explicitamente definida; a **média do período filtrado** é uma medida diferente.

## 6. Valores exibidos na versão visual de 09/11/2026

> **Fonte desta seção:** capturas do Power BI fornecidas pelo autor, e não uma extração independente das medidas DAX.

| Métrica | Valor mostrado | Referência / observação |
| --- | ---: | --- |
| IPCA 12M | 4,58% | 09/2026 |
| Variação mensal do IPCA 12M | +0,35 pp | Versus mês anterior |
| Distância da meta central | +1,58 pp | 4,58% − 3,00% |
| Meta SELIC — mês comum | 13,75% a.a. | 09/2026; variação exibida de −0,25 pp |
| SELIC efetiva — mês comum | 13,78% a.a. | 09/2026; variação exibida de −0,15 pp |
| Juros reais | 8,80% | 09/2026; variação exibida de −0,52 pp |
| IPCA acumulado no ano | 3,95% | Setembro/2026 |
| Meses acima do teto | 33,3% | 3 de 9 meses, conforme dashboard |
| USD/BRL — último do período | R$ 5,11 | Página Câmbio |
| EUR/BRL — último do período | R$ 5,74 | Página Câmbio |
| Amplitude USD — 12 meses fechados | 3,90% | Janela indicada: 11/2025 a 10/2026; status Moderada |

A ingestão da SGS 432 também retornou uma observação em **08/11/2026**, com valor **13,75% a.a.**. Essa é uma referência mais recente da fonte e **não deve ser confundida** com o mês comum de setembro usado nos cartões comparativos.

## 7. Reconciliação e critérios de aceite

1. Confirmar no SQL Server o mês de referência e as datas efetivamente disponíveis em cada série.
2. Recalcular manualmente pelo menos um IPCA 12M por composição de 12 fatores, sem arredondar antes do resultado final.
3. Comparar a **última meta no mês** com a **média mensal da SELIC efetiva** no mesmo mês; verificar a variação mensal de cada uma **separadamente**.
4. Recalcular os juros reais pela razão de fatores e comparar SQL, DAX e cartão.
5. Conferir os filtros `currency` e a janela de 12 meses da amplitude cambial; confirmar que o valor não foi apresentado como volatilidade.
6. Testar o seletor de datas e documentar quais cartões usam **último dado global**, **último dado do período** ou **mês comum**.
7. Registrar, por métrica: **mês, valor independente, valor SQL, valor DAX, diferença e resultado**. Como referência de rigor, comparar taxas com tolerância de `0,0001 pp` **antes** do arredondamento visual, se a precisão da fonte permitir.

Exemplo de consulta de conferência da Meta SELIC no mês comum:

```sql
SELECT TOP (1)
    data,
    valor AS meta_selic_aa
FROM dbo.fx_macro_indicadores
WHERE indicador = 'SELIC_META'
  AND data >= '20260901'
  AND data <  '20261001'
ORDER BY data DESC;
```

**Limite da revisão documental:** as fórmulas DAX atuais não foram extraídas do arquivo `.pbix` nesta revisão. As regras acima representam o contrato esperado e o que foi exibido nas capturas; confirmar a implementação efetiva no Power BI continua sendo uma etapa de auditoria.

---

**Documento relacionado:** [REVISAO.md](REVISAO.md) · [README principal](../README.md)
