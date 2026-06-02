# Análise de Viabilidade Técnica — Assistente RAG NovaTech
**Exercício Desenvolvedor 1.1**  
**Papel:** Desenvolvedor  
**Projeto:** Assistente de IA para Atendimento — NovaTech Logística

---

## 1. Escopo da análise

O Tech Lead pediu avaliação de viabilidade técnica considerando as características específicas da base documental da NovaTech e o impacto do gerenciamento de contexto na arquitetura do pipeline de RAG.

As fontes de dado são:

| Fonte | Qtde | Formato | Desafio principal |
|-------|------|---------|-------------------|
| SharePoint | ~800 docs | PDF, DOCX | Tabelas, fluxogramas como imagem, OCR (~15% escaneados) |
| Confluence | ~400 páginas | HTML/Wiki | Links internos, macros customizadas |
| Pasta de rede | ~50 planilhas | XLSX | Fórmulas interdependentes, dados relacionais |

---

## 2. Análise por tipo de fonte

### 2.1 PDFs com tabelas complexas (tabelas de frete com 15+ colunas)

**Desafio para o pipeline:**
Extratores padrão de PDF (PyMuPDF, pdfplumber) lêem texto linearmente. Uma tabela de 15 colunas é serializada como uma sequência de células sem indicação de qual coluna pertence ao quê. O resultado é texto como `"Sul 1.2 1.3 Sudeste 1.0 1.1..."` — ambíguo e irrecuperável por similaridade semântica.

**Impacto na qualidade das respostas:**
O LLM recebe texto fragmentado e, sem o contexto estrutural da tabela, pode misturar valores de colunas diferentes. Exemplo real: a PROC-042-v1 e PROC-042-v2 têm tabelas de multiplicadores que diferem em todos os valores — um extrator ruim pode produzir chunks que mesclam as duas tabelas sem distinção.

**Estratégia de tratamento:**
- Usar `pdfplumber` com extração de tabelas estruturadas (retorna dicts com cabeçalho).
- Serializar tabelas como Markdown estruturado antes do chunking: `| Região | Multiplicador |`.
- Adicionar metadado `contains_table=True` ao chunk para permitir rankeamento diferenciado.
- Para tabelas críticas (tabelas de SLA, multiplicadores de frete): criar chunks dedicados que incluam apenas a tabela + seu heading, sem misturar com texto narrativo.

---

### 2.2 PDFs escaneados (~15% da base, OCR necessário)

**Desafio para o pipeline:**
Documentos escaneados são imagens. Não há texto nativo para extração. A qualidade do OCR varia com a resolução do scan, inclinação da página e qualidade da impressão original.

**Impacto na qualidade das respostas:**
OCR com 95% de acurácia ainda produz ~1 erro a cada 20 palavras. Em documentos técnicos com termos como "CT-e", "ANTT", "PROC-042", um erro de OCR pode destruir a capacidade do retrieval de encontrar o chunk. Pior: o LLM pode inferir um valor errado (ex: "7 dias" lido como "1 dias" por OCR ruim).

**Estratégia de tratamento:**
- Usar Azure Document Intelligence (ex-Form Recognizer) em vez de Tesseract: detecta layout, tabelas e formulários em documentos corporativos com acurácia superior.
- Implementar confidence score por palavra na ingestão. Chunks com confidence médio < 85% devem ser sinalizados com metadado `ocr_confidence=low` e excluídos do índice até revisão humana.
- Separar pipeline de ingestão para docs escaneados com etapa de validação manual antes de publicar no índice.

---

### 2.3 Wiki do Confluence (links internos, macros customizadas)

**Desafio para o pipeline:**
Links internos (`[ver PROC-042]`) perdem o destino quando a página é exportada como texto plano. Macros customizadas (ex: `{expand}`, `{table-of-contents}`) geram ruído na extração. Páginas com estrutura de "pai-filho" no Confluence podem ter contexto distribuído entre várias páginas interdependentes.

**Impacto na qualidade das respostas:**
Um chunk que diz "ver tabela na seção anterior" é inútil se a seção anterior não estiver no mesmo chunk. O assistente não tem como "clicar no link" para resolver a referência.

**Estratégia de tratamento:**
- Usar a API do Confluence para exportar páginas com resolução de links (substituir `[ver PROC-042]` pelo trecho referenciado inline, ou ao menos pelo título da página alvo).
- Pré-processar HTML antes de chunking: remover macros, resolver `<a href>` internos.
- Para hierarquias pai-filho: incluir breadcrumb da navegação como prefixo do chunk (`"Seção: Operações > Fretes > Especial"`).

---

### 2.4 Planilhas XLSX com fórmulas interdependentes

**Desafio para o pipeline:**
Planilhas com fórmulas (`=VLOOKUP(...)`, `=SE(...)`) são lógica de negócio, não dados. Exportar como texto plano produz apenas os valores calculados no momento da exportação, que ficam desatualizados quando a planilha muda.

**Impacto na qualidade das respostas:**
A tabela de fretes base é atualizada mensalmente. Se o pipeline ingere a planilha como snapshot, as respostas ficam desatualizadas até a próxima reindexação. Pior: o assistente não sabe que o valor está desatualizado.

**Estratégia de tratamento:**
- Não tratar planilhas como documentos narrativos. Para tabelas de referência (ex: `frete-base-AAAAMM.xlsx`): extrair apenas os dados tabelados (sem fórmulas) e serializar como Markdown.
- Implementar webhook ou trigger no SharePoint para reindexar automaticamente quando a planilha é modificada.
- Adicionar metadado `valid_until` nos chunks de planilhas, derivado do nome do arquivo (`frete-base-202412.xlsx` → válido até 31/12/2024).

---

## 3. Estimativa de tamanho da base em tokens

Usando a regra prática de ~0,75 palavras por token (1 token ≈ 1,33 palavras em português):

| Fonte | Estimativa de conteúdo | Tokens estimados |
|-------|----------------------|-----------------|
| 800 PDFs × 10 páginas × 250 palavras/página | 2.000.000 palavras | **~2,7M tokens** |
| 400 páginas wiki × 1.500 palavras | 600.000 palavras | **~800K tokens** |
| 50 planilhas × 500 células × 5 palavras | 125.000 palavras | **~167K tokens** |
| **TOTAL ESTIMADO** | | **~3,7M tokens** |

> **Observação crítica:** Esse número é o tamanho da base — não o que vai para o modelo de uma vez. O pipeline recupera apenas 3–5 chunks por query (~1.500–2.500 tokens). O total da base é relevante para: custo de ingestão (uma vez), custo de reindexação e qualidade do vocabulário para embeddings.

---

## 4. Análise de orçamento de contexto por query

Modelo de referência: GPT-4o com janela de 128K tokens.

| Componente | Tamanho estimado | Tipo |
|-----------|-----------------|------|
| System prompt (identidade, regras, guardrails) | ~300 tokens | Estático |
| Metadados do atendente (tier do cliente, ID do chamado) | ~50 tokens | Dinâmico/query |
| Histórico de conversa (sliding window 5 turnos) | ~1.000 tokens | Dinâmico/crescente |
| Chunks recuperados (5 × ~500 tokens) | ~2.500 tokens | Dinâmico/query |
| Pergunta do atendente | ~50 tokens | Dinâmico/query |
| **Total por query** | **~3.900 tokens** | |
| **Margem disponível** | ~124.000 tokens não usados | |

**Conclusão:** Para queries individuais, o orçamento é extremamente folgado com GPT-4o 128K. O risco não é overflow de contexto por query — é **context rot em sessões longas**.

---

## 5. Risco: efeito "Lost in the Middle"

O fenômeno *lost in the middle* (Liu et al., 2023) descreve a queda de atenção do modelo para informação posicionada no meio de contextos longos. O modelo tende a priorizar o início e o fim do prompt.

**Implicação para o pipeline NovaTech:**

Se o pipeline recuperar 5 chunks e posicioná-los sequencialmente no prompt, o chunk no meio (posição 3) recebe menos atenção. Para perguntas sobre multiplicadores de frete — onde os valores exatos importam — um chunk no meio com o dado correto pode ser ignorado em favor de um chunk no início com dado de versão errada.

**Mitigações:**
1. Limitar a 3 chunks em vez de 5 para queries de domínio único (ex: só frete, só SLA). Usar 5 apenas para queries multi-domínio.
2. Posicionar o chunk de maior score **sempre no início** do bloco de contexto.
3. Para informação crítica (valores numéricos, prazos): extrair e repetir no final do prompt como "Resumo dos dados-chave": `"Multiplicador Norte (v2): 1.8 | SLA Gold geral: 24h"`.

---

## 6. Estratégia de chunking recomendada

**Estratégia: chunking semântico por seção**, com as seguintes regras:

1. **Fronteiras primárias:** headings Markdown (`##`, `###`) ou títulos de seção em PDFs.
2. **Fronteiras adicionais:** início de tabela (`|`) como fronteira que nunca pode ser cortada no meio.
3. **Tamanho alvo:** 300–600 tokens por chunk. Nunca forçar splits no meio de uma tabela ou lista numerada.
4. **Overlap:** último parágrafo da seção anterior (máx. 100 tokens) como prefixo do chunk seguinte.
5. **Chunks de tabela:** tabelas críticas (multiplicadores, SLAs) são sempre chunks atômicos independentes, mesmo que pequenas (~80 tokens).

**Por que NÃO usar 512 tokens fixo:**
- Corta tabelas ao meio com alta probabilidade.
- Gera chunks com contexto arbitrário que não mapeia para intenções de query.
- Produz N chunks parecidos do mesmo documento, aumentando ruído no retrieval.

**Por que NÃO usar chunking muito grande (>1.000 tokens):**
- Aumenta ruído dentro do chunk (resposta correta misturada com informação irrelevante).
- Amplifica o efeito *lost in the middle* dentro do próprio chunk.
- Mais tokens consumidos por query → menos espaço para histórico de conversa.

---

## 7. Ponto crítico identificado na documentação da NovaTech

A coexistência de PROC-042-v1 e PROC-042-v2 no SharePoint sem hierarquia formal é o risco técnico mais alto do projeto. Durante a ingestão:

- Ambos os documentos serão indexados.
- Chunks de ambos serão recuperados para perguntas sobre multiplicadores de frete.
- O LLM receberá valores contraditórios no mesmo contexto.
- Sem instrução explícita, o LLM pode misturar ou escolher o valor errado.

**Mitigação técnica:**
- Campo `superseded_by` nos metadados durante ingestão: `PROC-042-v1.superseded_by = "PROC-042-v2"`.
- O retrieval aplica penalidade de score (-0,3) a chunks com `superseded_by != null`.
- O system prompt instrui: "Se chunks contraditórios estiverem presentes, apresente ambos ao atendente com as datas e indique qual é mais recente."
- **Requisito de processo:** Solicitar à NovaTech que formalize a obsolescência dos documentos no SharePoint antes do go-live. Sem isso, o pipeline de ingestão precisa inferir precedência por data — o que é frágil.

---

## 8. Iteração com o Claude (revisão crítica)

Após a análise inicial, o documento foi submetido ao Claude para revisão com o prompt:

> *"Você é um engenheiro sênior de ML especializado em RAG. Revise esta análise técnica e identifique: pontos fracos, estimativas otimistas e riscos não considerados."*

**Problemas adicionais identificados pelo Claude:**

1. **Estimativa de tokens subestimada:** A análise original usou 250 palavras/página para PDFs. Para documentos técnicos com tabelas densas e terminologia repetitiva, 300–400 palavras/página é mais realista. A base pode ter até 5M tokens — não 3,7M.

2. **Custo de embedding na ingestão:** 3,7M tokens × $0,0001/1K tokens (text-embedding-ada-002) = **~$370 na primeira ingestão**. Com reindexação mensal de ~10% da base: ~$37/mês. Não foi considerado no orçamento inicial.

3. **Risco de drift de vocabulary:** Com documentos do Confluence atualizados semanalmente, novos termos técnicos surgem sem reindexação. Um procedimento publicado na semana com nomenclatura diferente da base não será recuperado por similaridade. **Reindexação deve ser incremental e automatizada**, não manual.

4. **Ausência de fallback para documentos sem cobertura:** A análise não abordou o caso de perguntas sobre temas sem documento na base (ex: frete padrão < 500kg). O pipeline precisa detectar score baixo em todos os chunks recuperados (threshold < 0,3) e acionar o comportamento "não encontrei" explicitamente, sem deixar o LLM preencher a lacuna com conhecimento paramétrico.

**Incorporações na versão final:** os pontos 1 e 4 foram incorporados diretamente nesta análise. Os pontos 2 e 3 serão levados para o ADR de arquitetura do Tech Lead e para o plano de capacidade do Delivery Manager.

---

## 9. Conclusão de viabilidade

**O projeto é viável tecnicamente**, com os seguintes pré-requisitos:

| Requisito | Criticidade | Responsável |
|-----------|-------------|-------------|
| Formalizar obsolescência de PROC-042-v1 no SharePoint | Alta | NovaTech Operações |
| Pipeline de extração com suporte a tabelas estruturadas | Alta | Dev |
| Pipeline de OCR com confidence scoring para docs escaneados | Média | Dev |
| Webhook de reindexação incremental (Confluence + SharePoint) | Alta | Dev + NovaTech TI |
| Sistema de metadados de versão/vigência na ingestão | Alta | Dev |
| Threshold de score baixo → comportamento "não encontrei" | Alta | Dev |
| Janela deslizante de histórico para context rot | Média | Dev |

A redução de 12 para 2 minutos por chamado é alcançável para as categorias cobertas pela documentação formal. Para os ~15% de casos sem cobertura documental (carga danificada, seguro, frete padrão < 500kg), o assistente deve escalar consistentemente — e isso conta como comportamento correto, não falha.
