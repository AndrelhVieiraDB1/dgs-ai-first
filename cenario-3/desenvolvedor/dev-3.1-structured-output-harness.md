# Structured Output e Verificações Determinísticas — Harness de Código
**Exercício Desenvolvedor 3.1**
**Papel:** Desenvolvedor
**Projeto:** Assistente de IA para Atendimento — NovaTech Logística
**Tópico:** Harness Engineering

**Continuidade dos cenários anteriores:** o query endpoint do cenário 2 (T01–T03) já valida o *input* com Zod — mas o *output* do modelo seguia como texto livre, e os testes internos mostraram o custo disso: 12% de respostas incorretas e fonte ausente sem que nada bloqueasse. Este exercício fecha o outro lado do contrato: a resposta do modelo agora também é um contrato Zod, e dois guardrails do Product Specialist (cenário 2) deixam de ser instrução de prompt para virar código que bloqueia.

Artefatos produzidos no repositório `novatech-assistant` (local):

| Artefato | Caminho no repo |
|----------|-----------------|
| Schema Zod do structured output | `src/shared/types.ts` (`assistantResponseSchema`) |
| **Validador de resposta (harness)** | `src/services/response-validator.ts` |
| Testes unitários (21 casos) | `tests/unit/response-validator.test.ts` |

---

## 1. O schema Zod do structured output (gerado com Copilot)

O modelo passa a ser instruído a responder **sempre** neste JSON — e o que não bater com o formato é rejeitado programaticamente antes de chegar ao atendente:

```typescript
// src/shared/types.ts — junto dos demais contratos (fonte única de verdade, z.infer)
export const assistantResponseSchema = z
  .object({
    answer: z.string().min(1, "answer não pode ser vazio"),
    source_document: z
      .string()
      .min(1, "source_document é obrigatório (guardrail 1)"),
    confidence_score: z
      .number()
      .min(0, "confidence_score deve estar entre 0 e 1")
      .max(1, "confidence_score deve estar entre 0 e 1"),
  })
  .strict();

export type AssistantResponse = z.infer<typeof assistantResponseSchema>;
```

Decisões que importam (as duas primeiras vieram do code review — seção 3):

- **`.strict()`** — campo extra é rejeição, não tolerância. Sem isso o modelo pode "vazar" campos inventados (ex.: `internal_reasoning`) que acabariam renderizados no bot do Teams.
- **`confidence_score` com faixa `[0, 1]`** — `z.number()` sozinho aceita `-1` ou `7`; o HITL do harness (roteamento de baixa confiança para validação humana) depende dessa faixa ser confiável.
- O schema fica em `src/shared/types.ts`, seguindo a convenção do cenário 2: schemas Zod são a fonte única de verdade e os tipos TypeScript são inferidos, nunca duplicados à mão.

## 2. O `response-validator.ts` (gerado com Copilot, corrigido após o review)

Código completo em `src/services/response-validator.ts`. O fluxo, na ordem barata → cara, forma → conteúdo:

```
output bruto do modelo (string)
  1. JSON.parse            → falhou? rejeita ("malformed-json")
  2. schema Zod (strict)   → falhou? rejeita ("schema-violation")
  3. guardrail 1 (extra)   → source_document é placeholder ("N/A", "desconhecido", "-")? rejeita
  4. guardrail 2           → carga perigosa + devolução sem a negativa da POL-001 §3.2? BLOQUEIA
  qualquer falha           → log estruturado do MOTIVO (nunca o conteúdo) + resposta padrão segura
```

O contrato de saída é uma união discriminada — o chamador **não tem como** usar a resposta original quando a validação falha; o tipo só oferece o fallback:

```typescript
export type ValidationVerdict =
  | { ok: true; response: AssistantResponse }
  | { ok: false; reason: RejectionReason; fallbackAnswer: string };

export const SAFE_FALLBACK_ANSWER =
  "Não foi possível validar esta resposta automaticamente. " +
  "Por favor, consulte a documentação oficial da NovaTech ou " +
  "encaminhe a dúvida ao seu supervisor antes de responder ao cliente.";
```

**Guardrail 2 em detalhe** (o mais sutil): a POL-001 §3.2 diz que cargas perigosas ANTT classes 1–6 **não** são elegíveis para devolução pelo processo padrão. A verificação normaliza o texto (minúsculas + remoção de acentos via NFD, então `DEVOLUÇÃO` ≡ `devolucao`), detecta a coocorrência dos dois temas por radicais (`devoluc`/`devolv` pega devolução/devolver/devolvida; o vocabulário de carga perigosa inclui plural, "produto perigoso", "inflamável", "explosivo") e então exige que a resposta contenha uma **negativa explícita** (padrões como `não são elegíveis`, `não pode ser devolvid...`, `não é possível devolver`). A decisão de design central é ser **fail-closed**: se os dois temas aparecem e nenhuma negativa é detectável — inclusive paráfrases afirmativas que os regex não anteciparam ("basta abrir chamado no Portal...") — a resposta é bloqueada. Errar para o lado de bloquear uma resposta correta custa um fallback; errar para o lado de deixar passar custa um cliente instruído a devolver carga classe 3 pelo processo padrão.

## 3. Code review com o Claude — problemas reais encontrados e corrigidos

A primeira versão gerada pelo Copilot (registrada abaixo, resumida) foi submetida ao Claude para review. Versão inicial:

```typescript
// primeira versão (Copilot) — trechos com problema
const assistantResponseSchema = z.object({
  answer: z.string(),
  source_document: z.string(),
  confidence_score: z.number(),
}); // sem .strict(), sem faixa, sem min(1)

function checkDangerousCargo(answer: string): boolean {
  // bloqueia apenas se encontrar a frase afirmativa exata
  return /carga perigosa/.test(answer) &&
         /devolução/.test(answer) &&
         /é possível devolver/.test(answer);
}

if (!parsed.success) {
  console.log("Resposta inválida:", raw); // loga e...
  return { answer: raw };                 // ...deixa a resposta original seguir
}
```

Problemas apontados pelo review (todos reais, todos corrigidos):

1. **Schema sem `.strict()`** — aceitava campos extras silenciosamente. Um modelo que devolvesse `{ ..., debug: "..." }` passava, e o campo desconhecido seguiria até o bot. *Correção:* `.strict()` no schema.
2. **`confidence_score` sem faixa** — `z.number()` aceita `-1` e `7`; qualquer roteamento HITL baseado em "confiança < 0.7" fica sem sentido. *Correção:* `.min(0).max(1)`. (`NaN` o Zod já rejeita por padrão — verificado em teste.)
3. **Regex do guardrail 2 não cobria variações E era fail-open.** `/carga perigosa/` perdia `CARGAS PERIGOSAS` (caixa/plural), `/devolução/` perdia `devolver`/`devolucao` (flexão/acento); pior: a lógica só bloqueava se encontrasse a frase afirmativa exata "é possível devolver" — qualquer paráfrase afirmativa passava. *Correção:* normalização NFD + radicais + **inversão da lógica** (bloqueia a menos que a negativa esteja presente — fail-closed).
4. **Guardrail 1 reduzido ao schema** — `source_document: "N/A"` tem 3 caracteres e passava no `min(1)`. Presença sintática do campo não é citação de fonte. *Correção:* checagem determinística de placeholders (`n/a`, `nenhum`, `desconhecido`, `-`, `sem fonte`...).
5. **Falha só logava, não bloqueava — e com `console.log` do conteúdo bruto.** Viola o critério do guardrail ("a resposta é rejeitada e **substituída**"), o AGENTS.md (pino, nunca console.log) e loga conteúdo que pode citar dados de cliente. *Correção:* união discriminada que força o fallback + `pino` logando apenas `reason`/`issuePaths`/metadados, nunca o texto integral.

## 4. Prompt (probabilístico) × código (determinístico)

| Camada | O que faz | Garantia |
|--------|-----------|----------|
| System prompt (Dev 1.2) | *Pede* fonte, *pede* cautela com carga perigosa, *pede* JSON | Probabilística — o modelo obedece na maioria dos casos; os 12% de erro dos testes internos são exatamente o resíduo |
| `assistantResponseSchema` | Rejeita resposta fora do formato antes de qualquer uso | Determinística — 100% das respostas sem `source_document` são barradas |
| Guardrails 1 e 2 no validator | Rejeita fonte-placeholder; bloqueia carga perigosa + devolução sem a negativa | Determinística — não depende de o modelo "ter entendido" a POL-001 |

O prompt continua existindo e continua importante (reduz a taxa de rejeição, logo o custo de fallback); o harness existe para o dia em que o prompt falha. Regra prática adotada: **tudo que é critério de bloqueio de negócio precisa ter uma verificação em código; o prompt é otimização, não garantia.**

## 5. Verificação (rodada nesta máquina)

```
✓ tests/unit/response-validator.test.ts (21 tests)
 Test Files  1 passed (1)   Tests  21 passed (21)

> tsc -p .   (build sem erros, strict: true)
```

Casos cobertos: resposta válida aprovada; texto livre (não-JSON) rejeitado; `source_document` ausente/vazio rejeitado (guardrail 1 via schema); 7 placeholders de fonte rejeitados (guardrail 1 determinístico); `confidence_score` `-0.1`/`1.5`/`NaN`/string rejeitados; campo extra rejeitado (`strict`); afirmação de devolução de carga perigosa bloqueada; paráfrase afirmativa não prevista bloqueada (fail-closed); variação de caixa/acento/flexão bloqueada; resposta com a negativa correta da POL-001 **aprovada**; devolução comum sem carga perigosa **não** é afetada; carga perigosa sem devolução (frete especial do PROC-042) **não** é afetada — os dois últimos garantem que o guardrail não gera falso positivo nos fluxos legítimos.
