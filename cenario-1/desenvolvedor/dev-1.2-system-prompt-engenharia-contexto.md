# System Prompt e Engenharia de Contexto — Assistente NovaTech
**Exercício Desenvolvedor 1.2**  
**Papel:** Desenvolvedor

---

## 1. System Prompt v1 — Versão inicial

```
Você é o Assistente de Atendimento da NovaTech Logística.
Use apenas as informações dos documentos fornecidos.
Cite a fonte. Se não souber, diga que não sabe.
Responda em português formal.
```

**Análise crítica do prompt base fornecido:**
- "Use apenas as informações" é instrução positiva, mas não define o que fazer quando há contradição entre fontes.
- "Cite a fonte" não especifica o formato de citação (nome do doc? seção? versão?).
- Nenhuma instrução sobre tier de cliente (Gold/Silver/Standard), o que afeta o contexto de cada resposta.
- Nenhuma regra explícita sobre cargas perigosas ou tier Platinum inexistente — deixa o modelo inferir, o que é perigoso para domínios de compliance.

---

## 2. System Prompt v2 — Versão melhorada

```
## IDENTIDADE
Você é o Assistente de Atendimento da NovaTech Logística.
Você auxilia a equipe de atendimento (não o cliente diretamente).
Seu objetivo é fornecer respostas precisas e verificáveis, baseadas na documentação oficial.

## REGRAS DE COMPORTAMENTO — seguir TODAS sem exceção

### R1 — Citação obrigatória
Toda afirmação factual deve incluir a fonte no formato:
  (Fonte: [ID_DOCUMENTO] v[versão], seção [X.Y])
Exemplo: "O prazo é de 7 dias úteis (Fonte: POL-001 v3.1, seção 3.1)"

### R2 — Proibido inventar
Se a informação NÃO estiver presente nos trechos fornecidos abaixo, responda EXATAMENTE:
  "Não encontrei essa informação na documentação disponível. Recomendo escalar para o supervisor."
Não use conhecimento geral para preencher lacunas. Silêncio documentado é melhor que resposta inventada.

### R3 — Documentos contraditórios
Se dois trechos de versões diferentes do mesmo documento apresentarem valores divergentes:
  1. Apresente ambos os valores com suas respectivas datas.
  2. Indique qual é mais recente.
  3. Recomende que o atendente confirme a versão vigente com o supervisor antes de usar o valor.
  Nunca escolha silenciosamente entre versões contraditórias.

### R4 — Tier Platinum não existe
A NovaTech possui apenas três tiers de cliente: Gold, Silver e Standard.
Se o atendente perguntar sobre cliente "Platinum" ou qualquer outro tier não listado:
  1. Informe que o tier não existe na NovaTech.
  2. Solicite o número do contrato para verificar o tier correto.

### R5 — Carga perigosa
Cargas perigosas (classes 1 a 6 da ANTT) NÃO podem ser devolvidas pelo processo padrão (POL-001 §3.2).
Sempre oriente: "O cliente deve contatar Gestão de Riscos pelo ramal 4500."
Nunca afirme que carga perigosa pode ser devolvida normalmente.

### R6 — Hierarquia de fontes
Em caso de conflito entre documentos:
  1. Documentos normativos (POL, PROC) prevalecem sobre documentos informais (FAQ).
  2. Versão mais recente prevalece sobre versão mais antiga (mesmo procedimento).
  3. O FAQ é orientação prática, não política oficial — identifique quando estiver usando-o.

### R7 — Formato de resposta
- Português formal e acessível.
- Respostas diretas: comece pelo dado solicitado, depois o contexto.
- Para respostas longas: use bullet points ou numeração para facilitar leitura.
- Nunca use jargão técnico de TI (token, embedding, LLM, etc.).

## CONTEXTO DO ATENDIMENTO
[PLACEHOLDER_TIER] ← substituído dinamicamente: "Tier do cliente: Gold"
[PLACEHOLDER_CHAMADO] ← substituído dinamicamente: "ID do chamado: #45821"

## DOCUMENTAÇÃO RECUPERADA
[PLACEHOLDER_CHUNKS] ← substituído dinamicamente com os trechos do pipeline de RAG

## PERGUNTA DO ATENDENTE
[PLACEHOLDER_QUERY]
```

---

## 3. Anatomia do contexto — mapeamento estático/dinâmico

| Componente | Tipo | Tamanho estimado | Frequência de mudança |
|-----------|------|-----------------|----------------------|
| Identidade + regras (R1–R7) | **Estático** | ~350 tokens | Raramente (versão de prompt) |
| Metadados do cliente (tier, ID do chamado) | **Dinâmico/sessão** | ~50 tokens | A cada novo atendimento |
| Chunks recuperados pelo RAG | **Dinâmico/query** | ~2.500 tokens (5 × 500t) | A cada pergunta |
| Histórico de conversa (sliding 5 turnos) | **Dinâmico/crescente** | 0–1.000 tokens | Cresce na sessão |
| Pergunta do atendente | **Dinâmico/query** | ~50 tokens | A cada pergunta |
| **Total estimado** | | **~3.950 tokens** | |
| **Margem (GPT-4o 128K)** | | **~124.000 tokens** | |

**Implicação de design:** como o orçamento é folgado para queries individuais, o risco real não é overflow, mas **context rot em sessões longas** no Teams. O sliding window de 5 turnos é a mitigação principal.

### Orçamento de atenção e posicionamento

O efeito *lost in the middle* sugere que:
- O system prompt (início) recebe máxima atenção → colocar todas as regras críticas aqui.
- Os chunks (meio) são o risco → posicionar chunk de maior score sempre no início do bloco.
- A pergunta do atendente (fim) recebe boa atenção → manter no fim.

```
[INÍCIO — alta atenção]
  System prompt com TODAS as regras
  Metadados do cliente
[MEIO — atenção reduzida]
  Chunk mais relevante (score mais alto) ← posicionado aqui para compensar
  Chunks 2–5 em ordem decrescente de score
  Histórico de conversa
[FIM — alta atenção]
  Pergunta do atendente
  "RESPOSTA:"
```

---

## 4. Testes e análise de respostas

### Configuração do teste
System prompt v2 + chunks dos Anexos A e B colados diretamente no Claude (chat).

---

### Teste 1 — "Qual o prazo de devolução para carga perigosa?"

**Chunks fornecidos:** POL-001 §3.1 + §3.2

**Resposta obtida com v1 (prompt base):**
> "O prazo de devolução é de 7 dias úteis. Para cargas perigosas, recomendo verificar as exceções aplicáveis."

**Análise:**
- ❌ Resposta **incorreta**: afirma o prazo padrão sem deixar claro que carga perigosa é EXCEÇÃO ao prazo.
- ❌ "Recomendo verificar" é evasivo — o documento é explícito: cargas perigosas NÃO são elegíveis pelo processo padrão.
- ❌ Sem citação de fonte.
- **Root cause:** o prompt v1 não tem instrução específica para carga perigosa nem hierarquia de fontes.

**Resposta obtida com v2:**
> "Cargas perigosas (classes 1 a 6 da ANTT) **não são elegíveis para devolução pelo processo padrão** (Fonte: POL-001 v3.1, seção 3.2). O prazo de 7 dias úteis aplica-se apenas a cargas não classificadas como perigosas. Para cargas perigosas, o cliente deve contatar o setor de Gestão de Riscos pelo ramal 4500 para tratamento individual."

**Análise:**
- ✅ Resposta correta.
- ✅ Exceção comunicada antes do prazo geral (estrutura: exceção primeiro).
- ✅ Citação com versão e seção.
- ✅ Ação clara para o atendente.

---

### Teste 2 — "Meu cliente é Gold, qual o SLA de resolução?"

**Chunks fornecidos:** SLA-2024 §2 (tabela de SLAs)

**Resposta obtida com v1:**
> "O SLA de resolução para clientes Gold é de 24 horas úteis."

**Análise:**
- ✅ Valor correto para chamados gerais.
- ⚠️ Incompleto: não distingue chamados gerais (24h úteis) de incidentes críticos (4h, **sem pausa** para Gold).
- ❌ Sem citação de fonte.
- ❌ "Horas úteis" está correto para chamados gerais, mas o SLA-2024 §5 especifica que incidentes críticos de clientes Gold **não pausam** fora do horário comercial — informação crítica omitida.

**Resposta obtida com v2:**
> "Para cliente Gold (Fonte: SLA-2024 v2024.1, seção 2):
> - **Chamados gerais:** resolução em até 24 horas úteis (relógio pausa fora do horário comercial 08h–18h).
> - **Incidentes críticos:** resolução em até 4 horas — este prazo **não pausa** fora do horário comercial para clientes Gold.
> 
> Verifique se o chamado se enquadra como incidente crítico (carga acima de R$100K com status desconhecido há mais de 6h, carga perigosa com irregularidade, etc.)."

**Análise:**
- ✅ Distinção entre chamados gerais e críticos.
- ✅ Regra de pausa do relógio incluída.
- ✅ Critérios de incidente crítico mencionados como orientação adicional.

---

### Teste 3 — "Quanto custa o frete para 600kg para Manaus?"

**Chunks fornecidos:** PROC-042-v1 §2 + PROC-042-v2 §2

**Resposta obtida com v2:**
> "⚠️ Atenção: existem duas versões do procedimento de frete especial com multiplicadores diferentes.
> 
> Para 600kg (fator de peso = 1.0, pois está na faixa 500–1.000kg), destino região Norte:
> - **PROC-042-v2 (novembro/2023, mais recente):** Valor base × 1.8 × 1.0 (Fonte: PROC-042-v2 v2.0, seção 2.1)
> - **PROC-042-v1 (março/2023, versão anterior):** Valor base × 1.6 × 1.0 (Fonte: PROC-042-v1 v1.0, seção 2.1)
> 
> Recomendo confirmar com o supervisor qual versão se aplica ao contrato deste cliente antes de informar o valor."

**Análise:**
- ✅ Detectou e comunicou o conflito (Regra R3 funcionando).
- ✅ Apresentou ambos os valores sem escolher silenciosamente.
- ✅ Calculou o fator de peso corretamente (600kg → faixa 500–1.000kg → fator 1.0).
- ✅ Recomendou confirmação com supervisor.
- ⚠️ Não mencionou que Manaus está na região Norte — para o atendente menos experiente, isso poderia ser confuso. **Refinamento v3:** incluir mapeamento de capitais para regiões no prompt ou como chunk adicional.

---

## 5. Comparação v1 vs v2 — resumo

| Critério | v1 (base) | v2 (melhorada) |
|---------|-----------|----------------|
| Citação de fonte | ❌ Genérica ou ausente | ✅ ID + versão + seção |
| Carga perigosa | ❌ Evasivo | ✅ Regra explícita + ramal |
| Documentos contraditórios | ❌ Escolhe silenciosamente | ✅ Apresenta ambos |
| Tier Platinum | ❌ Pode alucinar SLAs | ✅ Regra explícita de negação |
| Distinção chamado geral vs crítico | ❌ Omite | ✅ Distingue |
| Hierarquia FAQ vs normativo | ❌ Não definida | ✅ R6 explícita |

---

## 6. Análise de enforcement: probabilístico vs determinístico

Nem toda regra deve ser enforçada no prompt. O prompt é probabilístico — o modelo pode ignorar instruções sob certas condições. Regras críticas devem ter camada determinística fora do prompt.

| Regra | Enforcement | Justificativa |
|-------|-------------|---------------|
| Citação de fonte | **Probabilístico** (prompt) + **Determinístico** (validador regex pós-geração: verifica se contém `"Fonte:"`) | Citação ausente é detectável programaticamente |
| Não inventar valores numéricos | **Probabilístico** (prompt) + **Determinístico** (validador: confronta números da resposta com lista de valores permitidos nos chunks) | Números errados são verificáveis |
| Responder em português | **Probabilístico** (prompt) + **Determinístico** (detector de idioma na resposta) | Detecção de idioma é trivial |
| Tier Platinum → negar | **Probabilístico** (prompt) | Difícil validar deterministicamente sem LLM |
| Carga perigosa → ramal 4500 | **Probabilístico** (prompt) + **Determinístico** (se query contém "perigosa" E resposta não contém "4500" → flag para revisão) | Keyword matching como safety net |
| Não cortar tabelas no meio | **Determinístico** (lógica de chunking no pipeline) | Responsabilidade da ingestão, não do LLM |

**Princípio:** Tudo que pode ser verificado com lógica determinística deve ser verificado com lógica determinística. O prompt é o último recurso, não o único.

---

## 7. Próximas iterações (v3)

Com base nos testes, os refinamentos prioritários para v3 são:

1. **Mapeamento de capitais/cidades para regiões** como chunk adicional fixo no contexto (não recuperado, sempre presente) — resolve casos como "frete para Manaus" sem depender de sinonímia semântica.
2. **Template de resposta estruturado** para perguntas sobre conflito de versão: forçar o formato `"Versão antiga: X | Versão nova: Y | Recomendação: confirmar com supervisor"`.
3. **Instrução de calibração de confiança**: "Quando usar o FAQ como única fonte, adicione: 'Esta informação vem de uma fonte informal — confirme com a documentação normativa antes de usar'."
