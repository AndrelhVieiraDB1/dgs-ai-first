# Revisão Crítica de Código Gerado por IA — Módulo de Feedback
**Exercício Desenvolvedor 3.2**
**Papel:** Desenvolvedor
**Projeto:** Assistente de IA para Atendimento — NovaTech Logística
**Tópico:** Revisão Crítica de Outputs de IA

**Código sob revisão:** o `feedback-handler.ts` gerado pelo Copilot (fornecido no cenário), destinado a `/src/functions/feedback/handler.ts`. **Referência de conformidade:** o AGENTS.md do projeto — *TypeScript strict, Zod para validação de input, pino para logging (nunca console.log), nunca logar dados pessoais, imports estáticos no topo.*

Artefatos produzidos no repositório `novatech-assistant` (local):

| Artefato | Caminho no repo |
|----------|-----------------|
| Contrato + validação Zod do feedback | `src/functions/feedback/validator.ts` |
| Persistência (Cosmos, import estático, cliente único) | `src/functions/feedback/store.ts` |
| **Handler reescrito** | `src/functions/feedback/handler.ts` |
| Redação de dados pessoais no logger | `src/shared/logger.ts` (paths `attendantEmail`, `email`) |
| Config Cosmos tipada fail-fast | `src/shared/config.ts` (`getCosmosConfig`) |
| Testes unitários (12 casos novos) | `tests/unit/feedback-{validator,handler}.test.ts`, `tests/unit/logger.test.ts` |

---

## 1. Minha revisão (feita ANTES de consultar o Claude)

| # | Problema | Classificação |
|---|----------|---------------|
| 1 | `(await request.json()) as any` — nenhuma validação; o body entra no fluxo com formato arbitrário | **Violação do AGENTS.md** (Zod obrigatório) + **segurança** (mass assignment: qualquer campo do atacante vira documento no banco) |
| 2 | `console.log("Feedback recebido:", JSON.stringify(feedback))` | **Violação do AGENTS.md** (pino, nunca console.log) |
| 3 | O log do item 2 inclui `attendantEmail` — dado pessoal do atendente em log de aplicação | **Violação do AGENTS.md** + **segurança/LGPD** (log é replicado, retido e acessível fora do controle de acesso do banco) |
| 4 | `require("@azure/cosmos")` dinâmico dentro do handler | **Violação do AGENTS.md** (imports estáticos no topo) — além de quebrar tree-shaking/análise estática e mascarar erro de dependência até o primeiro request |
| 5 | `new CosmosClient(...)` **a cada request** | **Bug potencial** (performance): abre conexão nova por feedback; sob carga, esgota conexões |
| 6 | `process.env.COSMOS_CONNECTION_STRING` sem verificação — `undefined` só estoura dentro do SDK, no primeiro request | **Bug potencial** (e violação do padrão de config tipada fail-fast do projeto, T02) |
| 7 | Nenhum try/catch — falha do Cosmos vira exceção não tratada (500 genérico do host, possivelmente com detalhe interno) | **Bug potencial** + **segurança** (vazamento de detalhe de infra na resposta) |
| 8 | `rating`, `queryId`, `comment` sem qualquer validação de domínio (rating aceita `"banana"`) | **Bug potencial** (dados inúteis/corrompidos no container; consequência direta do item 1) |
| 9 | `app.http` sem `authLevel` — no modelo v4 o default é `anonymous`: endpoint público gravando no banco | **Segurança** |
| 10 | Contrato de resposta pobre: `200` com body `"OK"` texto puro, sem `id` do feedback criado | Menor (consistência com o padrão de erro do query endpoint) |

## 2. Revisão do Claude (segunda opinião)

Prompt: o módulo + o resumo do AGENTS.md + "revise antes do merge, classifique cada problema". Achados do Claude, consolidados:

1. `as any` sem validação Zod — violação do AGENTS.md e vetor de injeção de documento arbitrário no Cosmos (coincide com meus itens 1 e 8, que o Claude tratou como um único achado com duas consequências).
2. `console.log` com o objeto completo, incluindo `attendantEmail` — dupla violação do AGENTS.md; recomendou também **redação em profundidade no próprio logger** (paths `attendantEmail`/`email` no redact do pino), para o caso de um call site futuro repetir o erro (meus itens 2 e 3 + uma mitigação que eu não tinha listado).
3. `require` dinâmico — violação do AGENTS.md (meu item 4).
4. `CosmosClient` por request — recomendou cliente único por processo, lazy (meu item 5).
5. Connection string sem fail-fast (meu item 6).
6. Ausência de tratamento de erro na chamada ao Cosmos (meu item 7).
7. `authLevel` ausente → `anonymous` no v4 (meu item 9).
8. **Ausência do parâmetro `InvocationContext`** na assinatura — sem `invocationId` não há correlação de logs por invocação, padrão que o próprio repo já usa no query endpoint (eu não tinha listado).
9. **`timestamp` gerado no handler é o único carimbo** — aceitável, mas notou que sem `id` próprio o documento fica dependente do id automático do Cosmos, dificultando idempotência/rastreio (relacionado ao meu item 10, mais bem fundamentado).
10. Sugeriu avaliar se **armazenar** `attendantEmail` em claro é necessário (minimização/retenção LGPD) — não é bug de código; encaminhado como pauta ao Tech Lead/Product Specialist, não resolvido em silêncio na reescrita.

## 3. Comparação honesta

- **Interseção quase total nos itens críticos:** os 4 achados mínimos do exercício (`as any`, `console.log`, `require` dinâmico, e-mail em log) apareceram nas duas listas — eram os mais evidentes.
- **O que o Claude pegou e eu não:** a ausência do `InvocationContext` (quebra o padrão de correlação de logs do próprio repo) e a mitigação de redact no logger. Também foi mais preciso no *porquê* dos itens (ex.: citou o default `anonymous` do modelo v4 de imediato; eu precisei confirmar na documentação).
- **O que eu peguei e o Claude só pegou com contexto:** na primeira tentativa, sem o AGENTS.md no prompt, o Claude não apontou pino nem a proibição de dado pessoal em log — sugeriu "considerar um logger estruturado" como melhoria genérica. Com o AGENTS.md anexado, os itens viraram violações objetivas. **Lição: a revisão por IA é tão boa quanto o contexto de projeto que ela recebe** — o AGENTS.md é input obrigatório do review, não só da geração.
- **Divergência de julgamento:** o Claude classificou o `200 "OK"` como estilo; eu mantive como problema de contrato (o painel web do PS vai precisar do `id`). Na reescrita prevaleceu `201 { id }`.
- Nenhum achado do Claude era inventado; nenhum precisou ser descartado. A soma das listas (12 itens únicos) é melhor que qualquer uma isolada — o valor do fluxo é a **união com julgamento humano por cima**, não a substituição.

## 4. Código reescrito (com Copilot, guiado pela lista consolidada)

Estrutura final — validação, persistência e HTTP separados (padrão do query endpoint):

```typescript
// src/functions/feedback/validator.ts — resolve itens 1 e 8
export const feedbackRequestSchema = z
  .object({
    queryId: z.string().uuid("queryId deve ser um UUID"),
    rating: z.number().int().min(1).max(5),
    comment: z.string().max(2000).optional(),
    attendantEmail: z.string().email().max(254),
  })
  .strict(); // campo extra = 400; nada além do contrato chega ao Cosmos
```

```typescript
// src/functions/feedback/store.ts — resolve itens 4, 5 e 6
import { CosmosClient, type Container } from "@azure/cosmos"; // estático, no topo

let container: Container | undefined;
function getFeedbackContainer(): Container {
  if (!container) {
    const cosmos = getCosmosConfig(); // fail-fast tipado (padrão T02)
    const client = new CosmosClient(cosmos.COSMOS_CONNECTION_STRING);
    container = client.database(cosmos.COSMOS_DATABASE).container(cosmos.COSMOS_FEEDBACK_CONTAINER);
  }
  return container; // cliente único por processo, lazy
}
```

```typescript
// src/functions/feedback/handler.ts — resolve itens 2, 3, 7, 9, 10 (trecho)
const log = requestLogger(context.invocationId); // pino + correlação (achado 8 do Claude)
// ...
try {
  await store.save(feedback);
} catch (error) {
  log.error({ reason: "store-failure", err: error, feedbackId: feedback.id },
    "feedback: falha ao persistir no Cosmos");
  return { status: 502, jsonBody: { error: { code: "FEEDBACK_STORE_UNAVAILABLE" } } };
}
// Sem attendantEmail nem comment: dado pessoal / texto livre nunca em log.
log.info({ feedbackId: feedback.id, queryId: feedback.queryId, rating: feedback.rating },
  "feedback: registrado");
return { status: 201, jsonBody: { id: feedback.id } };
```

```typescript
app.http("feedback", { methods: ["POST"], authLevel: "function", route: "feedback",
  handler: feedbackHandler }); // item 9: nunca mais anonymous por omissão
```

Defesa em profundidade adicional (recomendação 2 do Claude): `attendantEmail`/`email` entraram nos paths de **redact do pino** — mesmo que um call site futuro logue o objeto inteiro por engano, o valor sai como `[REDACTED]` (comprovado em teste).

## 5. Verificação (rodada nesta máquina)

```
✓ tests/unit/feedback-validator.test.ts (7 tests)
✓ tests/unit/feedback-handler.test.ts (4 tests)
✓ tests/unit/logger.test.ts (4 tests)         ← inclui redação de attendantEmail/email
 Test Files  7 passed (7)   Tests  54 passed (54)   (suíte completa do repo)

> tsc -p .   (build sem erros, strict: true)
```

Destaques da suíte: `rating` `0`/`6`/`3.5`/`"4"`/`null` rejeitados; campo extra rejeitado (`strict`); input inválido retorna 400 **sem tocar o store**; falha do Cosmos retorna `502` com código genérico e o teste comprova que o detalhe interno (`connection refused em 10.0.0.7`) **não** aparece na resposta; e-mails nunca aparecem no output do logger. O handler é testável sem Cosmos real via `createFeedbackHandler(store)` — injeção do `FeedbackStore`.
