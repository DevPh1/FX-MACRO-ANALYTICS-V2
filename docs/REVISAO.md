# Revisão técnica e evidências de execução — FX Macro Analytics V2

> **Atualizado em:** 09/11/2026\
> **Objetivo:** separar o histórico da revisão inicial, as mudanças implementadas na V2, as evidências de execução e as verificações ainda pendentes.

## 1. Contexto e histórico

A revisão inicial partiu do commit `68595c6d7c3d14e3abc09f572c230852aedfff99`. Naquela etapa, a documentação descrevia **quatro séries**, **10 regras de validação** e um Power BI ainda pendente de atualização.

A evolução registrada na conversa do projeto incluiu a **Meta SELIC (SGS 432)**, a criação de uma quinta view GOLD, a ampliação para **11 testes SQL** e a reformulação visual das páginas **Visão Macro, Câmbio e Inflação**.

**Controle de versão:** o commit acima é uma **referência histórica**, não o hash da versão final. Esta revisão documental **não** comprova que as alterações já foram enviadas ao repositório remoto.

## 2. Alterações técnicas implementadas

### 2.1 Configuração e ingestão

- `src/common.py`: `SERIES` inclui `IPCA` (`433`), `USD_BRL` (`1`), `EUR_BRL` (`21619`), `SELIC` (`1178`) e `SELIC_META` (`432`).
- `src/ingestion/bcb_api.py`: percorre `SERIES` dinamicamente, consulta a API SGS, valida estrutura e valores, e gera CSV/JSON por série.
- `data/RAW/manifest.json`: registra metadados e hashes SHA-256; os snapshots ficam em `data/RAW/snapshots/<run_id>/`.
- `src/transformation/load_silver.py`: carga adaptada para gravar `SELIC_META` junto de IPCA e SELIC efetiva em `dbo.fx_macro_indicadores`; câmbio continua nas tabelas `silver.usd_brl` e `silver.eur_brl`.

A publicação dos arquivos RAW ocorre **antes e fora** da transação SQL. O manifest é publicado por último, mas a substituição de todos os CSVs não é atomicamente coordenada com a gravação do banco. Evitar execuções concorrentes.

### 2.2 Camadas SQL

**GOLD — 5 views executadas:**

1. `01_vw_gold_ipca.sql`
2. `02_vw_gold_selic.sql`
3. `03_vw_gold_macro.sql`
4. `04_vw_macro_monthly.sql`
5. `05_vw_gold_selic_meta.sql` — nova view `dbo.vw_gold_selic_meta`, com `data` e `selic_meta_aa`.

**ANALYTICS — 3 views executadas:**

1. `01_vw_fx_monthly_summary.sql`
2. `02_vw_macro_ipca_12m.sql`
3. `03_vw_macro_real_rate.sql`

O executor `src/transformation/sql_runner.py` percorre os arquivos `*.sql` em ordem alfabética. O orquestrador `src/transformation/run_all.py` executa carga, views GOLD, views ANALYTICS e validação dentro de `engine.begin()`; uma falha nessa etapa deve provocar rollback das operações SQL transacionais.

### 2.3 Validação — 11 regras

O contrato `EXPECTED` em `src/transformation/run_validation.py` e a consulta `sql/Validation/validate_gold.sql` incluem:

| Regra | Finalidade |
| --- | --- |
| `GOLD_VAZIA` | Identificar ausência de registros na view mensal |
| `IPCA_INVALIDO` | Identificar valores ou datas inválidos de IPCA |
| `SELIC_INVALIDA` | Identificar valores ou datas inválidos da SELIC efetiva |
| `SELIC_META_INVALIDA` | Identificar ausência de Meta SELIC ou registros com valor/data inválidos |
| `JUROS_REAIS_NULO` | Detectar juros reais nulos em períodos com IPCA 12M |
| `DATA_DUPLICADA` | Detectar datas repetidas na view mensal |
| `DATA_NULA` | Detectar datas nulas na view mensal |
| `CAMBIO_VAZIO` | Detectar ausência de dados cambiais |
| `LACUNA_IPCA` | Detectar lacunas entre meses de IPCA |
| `MOEDAS_AUSENTES` | Confirmar presença das duas moedas no resumo cambial |
| `IPCA_12M_INVALIDO` | Detectar IPCA 12M nulo após a formação da janela mínima |

**Limite dos testes:** `SELIC_META_INVALIDA` verifica presença e valores negativos/nulos, mas não certifica sozinho a correspondência com a decisão histórica do Copom, a atualização recente da série nem a exatidão de todas as medidas DAX.

## 3. Evidência de execução ponta a ponta até o SQL Server

**Data:** 09/11/2026\
**Comando informado na sessão:** `python src/transformation/run_all.py --refresh`\
**Identificador da ingestão:** `20261109T023653213523Z`

### 3.1 Séries recebidas e persistidas

| Série | Código SGS | Observações confirmadas na carga |
| --- | ---: | ---: |
| IPCA | 433 | 561 |
| USD/BRL | 1 | 2.507 |
| EUR/BRL | 21619 | 2.505 |
| SELIC efetiva | 1178 | 2.507 |
| Meta SELIC | 432 | 3.651 |
| **Total entre as tabelas** | — | **11.731** |

O total é a soma das observações confirmadas em **tabelas diferentes**; não representa 11.731 linhas em `dbo.fx_macro_indicadores`.

### 3.2 Resultado das transformações

- **5/5 views GOLD** executadas.
- **3/3 views ANALYTICS** executadas.
- **11/11 testes de qualidade** executados com `Erros: 0`.
- Mensagem final registrada: `Transformações validadas e confirmadas na mesma transação.`

**Conclusão sustentada pelo log:** a execução relatada concluiu ingestão, carga no SQL Server, atualização das oito views e validação SQL sem erro. Isso é evidência de integração **até o banco**, mas não equivale a uma auditoria automática do conteúdo do arquivo `.pbix`.

## 4. Evidência visual do Power BI

As capturas compartilhadas em 09/11/2026 mostram três páginas atualizadas:

| Página | Conteúdo observado |
| --- | --- |
| **01 — Visão Macro** | IPCA 12M, Meta SELIC, juros reais e SELIC efetiva; mês comum de referência e gráficos de IPCA mensal × SELIC e juros reais |
| **02 — Câmbio** | USD/BRL, EUR/BRL, médias mensais, faixas mínima/média/máxima e amplitude USD em 12 meses fechados |
| **03 — Inflação** | IPCA 12M versus meta/teto, tendência, distância da meta, meses acima do teto e IPCA acumulado no ano |

Na última captura da **Visão Macro**, os cartões indicavam referência comum de **09/2026** para Meta SELIC, SELIC efetiva e juros reais. A página **Câmbio** explicitava amplitude em **11/2025–10/2026**, uma janela diferente do intervalo de evolução exibido nos gráficos. A página **Inflação** diferenciava o acumulado no ano da métrica IPCA 12M usada para comparação com a meta.

Essas observações **não** confirmam, por si sós, que todas as medidas DAX foram auditadas ou que a versão `.pbix` final já está salva e publicada no GitHub.

## 5. Verificações históricas da revisão inicial

Na revisão anterior, constavam as seguintes verificações locais:

- `python -m unittest discover -s tests -v`: **9 testes locais aprovados**, **1 teste de integração ignorado** por ausência de banco configurado naquele ambiente.
- `python -m compileall -q src tests` e `git diff --check`: aprovados **na revisão anterior**.
- Conferência independente do snapshot antigo, abril de 2026:
  - 12 observações de IPCA na janela;
  - soma simples de IPCA: **4,31 pp**;
  - IPCA composto: **4,3917196715%**;
  - média da SELIC SGS 1178: **14,6375% a.a.**;
  - indicador de juros reais por razão de fatores: **9,8147442736%**.

Esses valores pertencem ao **snapshot antigo**. Não devem ser confundidos com a ingestão de novembro de 2026, nem tratados como uma nova execução da suíte após a inclusão da Meta SELIC.

## 6. Pendências de validação e publicação

A execução SQL da V2 foi demonstrada. Permanecem recomendadas, sem evidência de conclusão nesta revisão documental:

1. **Regressão após a quinta série:** executar novamente a suíte Python completa (`python -m unittest discover -s tests -v`) e revisar testes que presumam quatro séries ou 10 regras.
2. **Idempotência e rollback:** repetir a carga no mesmo snapshot, conferir contagens e executar teste controlado de falha em banco de desenvolvimento, sem afetar dados importantes.
3. **Reconciliação SQL ↔ Power BI:** comparar IPCA 12M, Meta SELIC no fim do mês, média mensal da SELIC efetiva, juros reais, câmbio e amplitude com cálculo independente; registrar tolerâncias e resultados.
4. **Filtro temporal:** testar mudança do período no Power BI e confirmar quais cartões são globais, do período ou do mês comum.
5. **Regras de negócio:** conferir no DAX os limiares do cenário macro, a classificação da amplitude, a vigência das metas e a janela da “média histórica”.
6. **Artefatos:** salvar o `.pbix` atualizado, revisar `requirements.txt`, `.gitignore`, scripts e documentação; verificar que credenciais e dados sensíveis não sejam publicados.
7. **GitHub:** registrar um novo commit e confirmar o `git push`; nenhum envio remoto foi realizado por esta revisão documental.

### Comandos úteis (PowerShell)

```powershell
# Na raiz do projeto, com o ambiente Python ativado
python -m unittest discover -s tests -v
python -m compileall -q src tests

# Verificar alterações antes de publicar
git status
git diff --check

# Após configurar FX_SQL_SERVER e FX_SQL_DATABASE,
# reprocessar o snapshot RAW existente sem consultar a API:
python src/transformation/run_all.py
```

**Segurança:** antes de executar a carga, confirme a instância SQL Server e o banco de destino. Para testes destrutivos ou injeção de falha, utilize um banco de desenvolvimento separado.

## 7. Limitações conhecidas

- Não há agendamento, lock distribuído nem atualização automática do Power BI Service implementados na versão documentada.
- A ingestão RAW e a transação SQL não formam uma única transação distribuída.
- A coleta diária usa uma janela de aproximadamente 3.650 dias; a cobertura histórica depende da série e da resposta da API.
- As classificações “cenário de atenção”, “restritivo” e “amplitude moderada/elevada” são **critérios internos**, não avaliações oficiais do Banco Central.
- A **amplitude cambial** não equivale à volatilidade de retornos.
- A data mais recente de uma série pode ser posterior ao **mês comum fechado** utilizado nos cartões de comparação.
- O bootstrap não substitui uma estratégia de migração de esquemas SQL antigos incompatíveis.

---

**Documentos relacionados:** [METRICAS.md](METRICAS.md) · [README principal](../README.md)
