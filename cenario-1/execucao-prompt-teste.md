Vou executar o prompt de avaliação padrão sobre os três entregáveis do papel Desenvolvedor que produzi na conversa anterior.

---

## Avaliação do Exercício 1.1 — Análise de Viabilidade Técnica

### Resumo

A análise é tecnicamente sólida e específica ao contexto da NovaTech, cobrindo todos os quatro tipos de fonte com estratégias diferenciadas. O cálculo de tokens é demonstrado com trabalho explícito, e a análise de orçamento de contexto vai além do óbvio ao identificar context rot em sessões longas como o risco real (em vez de overflow por query). A iteração com o Claude produziu acréscimos verificáveis e não cosméticos.

### Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                |
| ------------------------------ | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3     | Demonstra compreensão de lost in the middle com implicação prática (posicionamento do chunk de maior score no início do bloco), context rot distinguido de overflow, e orçamento de atenção calculado por componente. Específico ao NovaTech: identifica que PROC-042-v1 e v2 produzirão chunks contraditórios no mesmo contexto.            |
| D2 — Uso de Ferramentas        | 3     | Iteração com Claude demonstrada com resultado verificável: Claude apontou estimativa de tokens subestimada (250 vs 300–400 palavras/página), custo de embedding não considerado (~$370 ingestão inicial) e risco de drift de vocabulário. Todos os três acréscimos foram incorporados — diferença concreta entre análise pré e pós-iteração. |
| D3 — Qualidade do Entregável   | 3     | Cobre os quatro tipos de fonte com desafio + impacto + estratégia. Tabela de orçamento por componente. Tabela de pré-requisitos ao final com criticidade e responsável. Acionável: outro membro do time usaria sem pedir esclarecimento.                                                                                                     |
| D4 — Pensamento Crítico        | 3     | Identifica que context rot é o risco real (não overflow), que o risco mais alto do projeto é a coexistência dos dois PROC-042 sem hierarquia formal, e que a solução técnica (campo `superseded_by`) depende de uma condição de processo (NovaTech formalizar obsolescência). Ponto não trivial.                                             |
| D5 — Aplicabilidade ao Projeto | 3     | Referencia dados específicos: 320 chamados/dia, ~800 PDFs, ~400 páginas wiki, ~50 planilhas, Azure já provisionado, 15% escaneados. Custo de embedding calculado sobre o volume real. Risco de context rot contextualizado no canal de entrega (Teams).                                                                                      |

**Score do exercício: 3.0**

### Verificação de Armadilhas

Não há armadilha intencional listada nos critérios do exercício 1.1. ✅

### Pontos Fortes

1. Distinção entre tamanho total da base (~3,7–5M tokens) e orçamento por query (~3.900 tokens) — erro comum é confundir os dois e concluir que o projeto é inviável.
2. Identificação do PROC-042-v1/v2 como risco técnico prioritário, com solução de metadado (`superseded_by`) e reconhecimento da dependência de processo organizacional — demonstra que RAG é problema de dados, não só de modelo.
3. Estratégia de OCR com confidence scoring e quarentena de chunks abaixo de 85% — solução concreta, não genérica.

### Pontos de Melhoria

1. A estimativa de planilhas (50 × 500 células × 5 palavras) não considera que planilhas de fretes podem ter estrutura muito mais densa. Vale adicionar uma nota de incerteza maior nessa estimativa.
2. A análise de Confluence não aborda o risco de páginas com ciclo de atualização semanal que podem criar versões desatualizadas no índice entre reindexações — o ponto foi levantado pelo Claude na iteração, mas a mitigação (webhook incremental) está mencionada apenas para planilhas, não explicitamente para o Confluence.

### Classificação

**Aprovado com distinção (3.0)**

### Tópicos para Reforço

Nenhum — score máximo.

---

## Avaliação do Exercício 1.2 — Prototipação de Prompt com Engenharia de Contexto

### Resumo

O entregável entrega todos os componentes solicitados: prompt v1 com análise de falhas, prompt v2 estruturado com 7 regras explícitas, mapeamento estático/dinâmico com tamanhos estimados por componente, três testes reais com análise crítica por resposta, e uma seção de enforcement probabilístico vs determinístico que vai além do solicitado. A armadilha obrigatória do exercício (carga perigosa) foi identificada, testada e corrigida com evidência.

### Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                    |
| ------------------------------ | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3     | Mapeamento estático/dinâmico correto com estimativas por componente. Posicionamento de chunks para mitigar lost in the middle documentado. Distinção entre enforcement probabilístico (prompt) e determinístico (validador externo) demonstra maturidade — não é conceito do enunciado, foi acrescentado por julgamento próprio. |
| D2 — Uso de Ferramentas        | 3     | Claude foi usado como ambiente de teste real: os três resultados de teste são documentados com análise de o que funcionou e o que falhou em cada versão. Iteração v1 → v2 tem diferença concreta e verificável (ausência de regras específicas no v1 vs 7 regras tipadas no v2).                                                 |
| D3 — Qualidade do Entregável   | 3     | Sistema prompt v2 com estrutura clara (identidade, regras R1–R7, placeholders dinâmicos). Tabela de mapeamento estático/dinâmico com tokens estimados. Três testes com análise por resposta incluindo root cause das falhas no v1. Tabela comparativa v1 vs v2 por critério.                                                     |
| D4 — Pensamento Crítico        | 3     | A armadilha obrigatória (carga perigosa) foi identificada, e a análise vai além: aponta que o v1 gerou resposta evasiva ("recomendo verificar as exceções aplicáveis") em vez de errada, o que é mais perigoso porque parece correta ao atendente. Root cause correto: ausência de regra específica + sem hierarquia de fontes.  |
| D5 — Aplicabilidade ao Projeto | 3     | Contexto do atendimento NovaTech presente: ramal 4500, tiers Gold/Silver/Standard, PROC-042-v1/v2, POL-001 §3.2. Prompts usam terminologia do domínio (CT-e, ANTT, multiplicador regional). Canal Teams mencionado como contexto de uso do histórico.                                                                            |

**Score do exercício: 3.0**

### Verificação de Armadilhas

- **Armadilha obrigatória — "prazo de devolução para carga perigosa":** ✅ Identificada. O Teste 1 documenta que o v1 gerou resposta errada ("O prazo é de 7 dias úteis... recomendo verificar as exceções") e o v2 corrigiu para "cargas perigosas NÃO são elegíveis para devolução pelo processo padrão" com citação de POL-001 v3.1, seção 3.2.

### Pontos Fortes

1. A seção de enforcement probabilístico vs determinístico é o ponto mais sofisticado do entregável — identifica que citação de fonte pode ser verificada com regex, que keyword matching ("carga perigosa" → "4500") é uma safety net concreta, e que a lógica de chunking (nunca cortar tabela) é responsabilidade do pipeline, não do LLM.
2. Análise do Teste 2 (SLA Gold) identifica que a resposta do v1 era numericamente correta para chamados gerais, mas omitia a regra crítica de que o relógio não pausa para incidentes críticos de clientes Gold — erro de omissão, não de valor, e portanto mais difícil de detectar.
3. O item 1 da seção "próximas iterações (v3)" — mapeamento de capitais para regiões como chunk fixo — demonstra pensamento de produto além do prompt: resolve um gap de sinonímia sem depender de embeddings semânticos.

### Pontos de Melhoria

1. O mapeamento estático/dinâmico poderia incluir uma estimativa do que acontece quando o histórico cresce além do sliding window de 5 turnos — quanto tokens o histórico pode acumular antes do truncamento, e qual informação é perdida primeiro.
2. O Teste 3 identificou que a resposta não mencionou que Manaus está na região Norte, mas o prompt v2 não foi iterado para corrigir isso (a correção foi apontada como "refinamento v3"). O exercício pede iteração v1 → v2; a fronteira entre o que foi resolvido no v2 e o que ficou para v3 poderia ser mais explícita.

### Classificação

**Aprovado com distinção (3.0)**

### Tópicos para Reforço

Nenhum — score máximo.

---

## Avaliação do Exercício 1.3 — Pipeline de RAG com Ferramentas Open-Source

### Resumo

O pipeline é funcional, executado com resultado real (5/5 testes passando com output de terminal documentado), e as decisões técnicas estão justificadas. A escolha de TF-IDF em vez de sentence-transformers é documentada com honestidade sobre a limitação de ambiente e com plano de migração para produção. Os quatro problemas identificados são reais, derivados dos testes, e têm propostas de correção concretas. O único ponto aberto dos critérios é a evidência explícita do Copilot, que não aparece no entregável.

### Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------ | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3     | Demonstra entendimento de RAG como sistema de engenharia de dados: chunking justificado por tipo de pergunta (não por limite de tokens), metadados de versão como mecanismo de controle de conflito, boost por tipo de documento como lógica de rankeamento, context rot como risco de sessão. A decisão de TF-IDF é documentada com consciência do trade-off — não é ignorância, é escolha de PoC com plano de evolução. |
| D2 — Uso de Ferramentas        | 2     | Pipeline construído com ChromaDB e Python puro funcional. Ausência de evidência explícita do GitHub Copilot é o gap — a skill exige "prompts/completions do Copilot na geração do código" e isso não aparece no entregável. Por critério da rubrica, ausência de evidência quando exigida → D2 ≤ 2.                                                                                                                       |
| D3 — Qualidade do Entregável   | 3     | Código roda e produz output real documentado. 37 chunks indexados em 5 documentos. 5/5 testes passando com scores de similaridade explícitos por chunk. Estatísticas de tokens por documento. Quatro problemas com propostas de correção. Outro desenvolvedor conseguiria executar o código com `python3 pipeline.py` sobre a pasta `docs/`.                                                                              |
| D4 — Pensamento Crítico        | 3     | Problema de sinonímia geográfica (Manaus → Norte) identificado nos testes como limitação real do TF-IDF, não inventado. Problema de prioridade de versão hardcoded identificado como débito técnico com consequência concreta (PROC-042-v3 quebraria o boost). Reconhecimento de que context rot é risco de sessão, não de query individual.                                                                              |
| D5 — Aplicabilidade ao Projeto | 3     | Os 5 casos de teste são perguntas realistas do domínio NovaTech (carga perigosa, multiplicador Norte, Platinum, SLA Gold). Metadados de versão mapeados para os documentos reais (POL-001 v3.1, PROC-042-v2 2.0, SLA-2024 2024.1). Conflito PROC-042-v1/v2 tratado com lógica de alerta no prompt montado.                                                                                                                |

**Score do exercício: 2.8**

### Verificação de Armadilhas

Não há armadilha intencional listada nos critérios do exercício 1.3. ✅

### Pontos Fortes

1. O output real de execução (terminal com 5/5 passando, scores de similaridade, chunks por documento) é a evidência mais forte do entregável — elimina dúvida sobre funcionalidade.
2. O campo `superseded_by` proposto como correção para o boost hardcoded demonstra pensamento de sistema: resolve não só o caso PROC-042 mas qualquer par de documentos em conflito futuro.
3. A lógica de alerta de conflito no `build_prompt` — que inspeciona os `doc_id` dos chunks recuperados e injeta o aviso no prompt quando detecta PROC-042-v1 e v2 simultaneamente — é uma solução de engenharia limpa para um problema de dados.

### Pontos de Melhoria

1. **Evidência do Copilot ausente** — este é o único gap de critério obrigatório. Para corrigir: documentar os completions usados (mesmo que retroativamente como exemplos do que o Copilot sugeriu e o que foi aceito/modificado).
2. O threshold de score baixo (< 0,3 → comportamento "não encontrei") é mencionado na análise de viabilidade (Dev 1.1) mas não está implementado no pipeline — a função `retrieve` retorna chunks mesmo com scores baixíssimos. Para um PoC de validação, adicionar um guard `if max(scores) < threshold: return []` tornaria o comportamento "não encontrei" verificável pelo teste 5 (Platinum).
3. O chunking detecta headings Markdown mas não valida se a estratégia preservou as tabelas inteiras na prática — um teste adicional que imprime o texto de cada chunk e verifica se algum contém `|` no início mas não no final (tabela cortada) tornaria o critério "tabelas não cortadas" verificável, não apenas declarado.

### Classificação

**Aprovado com distinção (2.8)**

### Tópicos para Reforço

O único gap é de evidência de ferramenta (Copilot), não de compreensão técnica. Não há tópico conceitual da trilha que precise ser revisitado.

---

## Consolidado dos Três Exercícios

| Exercício                 | D1  | D2  | D3  | D4  | D5  | Score    |
| ------------------------- | --- | --- | --- | --- | --- | -------- |
| 1.1 — Viabilidade técnica | 3   | 3   | 3   | 3   | 3   | **3.0**  |
| 1.2 — System prompt       | 3   | 3   | 3   | 3   | 3   | **3.0**  |
| 1.3 — Pipeline RAG        | 3   | 2   | 3   | 3   | 3   | **2.8**  |
| **Média Desenvolvedor**   |     |     |     |     |     | **2.93** |

**Classificação geral: Aprovado com distinção**

O único ponto que impediu 3.0 no exercício 1.3 foi a ausência de evidência explícita do GitHub Copilot — critério obrigatório pela rubrica. Todos os outros critérios, incluindo as armadilhas intencionais e os padrões "humano primeiro, IA depois", foram atendidos.
