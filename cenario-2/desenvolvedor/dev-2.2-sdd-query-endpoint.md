# Implementação de Spec com Spec Driven Development — Query Endpoint
**Exercício Desenvolvedor 2.2**
**Papel:** Desenvolvedor
**Projeto:** Assistente de IA para Atendimento — NovaTech Logística

Artefatos produzidos no repositório `novatech-assistant` (local):

| Artefato | Caminho no repo |
|----------|-----------------|
| Plan (input do TL, registrado na spec) | `specs/query-endpoint/plan.md` |
| **tasks.md gerado** | `specs/query-endpoint/tasks.md` |
| Contrato request/response (Zod) | `src/shared/types.ts` |
| Validação de input | `src/functions/query/validator.ts` |
| HTTP trigger (Azure Functions v4) | `src/functions/query/handler.ts` |
| Testes unitários (12 casos) | `tests/unit/query-validator.test.ts`, `tests/unit/query-handler.test.ts` |

---

## 1. Conversão plan.md → tasks.md

O plan foi quebrado em **12 tasks atômicas** (T01–T12), cada uma com ID, descrição, critérios de aceite verificáveis, dependências explícitas e estimativa P/M/G — conteúdo completo em `specs/query-endpoint/tasks.md`. Resumo:

| ID | Task | Deps | Est. |
|----|------|------|------|
| T01 | Setup do endpoint POST /api/query com validação de input (Zod) | — | M |
| T02 | Configuração de ambiente tipada (fail-fast) | — | P |
| T03 | Logger estruturado (pino) | T02 | P |
| T04 | Erros de domínio + mapeamento HTTP | — | P |
| T05 | Retry com exponential backoff (só erros transitórios) | T04 | P |
| T06 | Serviço de embedding (Azure OpenAI) | T02–T05 | M |
| T07 | Busca top-5 (Azure AI Search) com metadado de vigência (ADR-0003) | T02–T05 | M |
| T08 | Prompt builder com context budget (ADR-0002) | T01 | M |
| T09 | Serviço de completion (GPT-4o) | T02–T05 | M |
| T10 | Response builder com `source_document` | T01, T07 | P |
| T11 | Orquestração do fluxo completo no handler | T01–T10 | M |
| T12 | Testes de integração (msw + fixtures do Anexo B) | T11 | M |

Decisões de decomposição que garantem atomicidade:

- **Cada task tem teste próprio e roda sem rede** — o critério "passa em `npm test` sem credenciais" torna cada aceite verificável mecanicamente, não "funcionar corretamente".
- **Infra transversal (config, logger, erros, retry) virou tasks separadas (T02–T05)** em vez de nascer dentro do primeiro serviço que precisar — evita que T06 vire um "M que é G" e permite paralelizar entre o dev pleno e o sênior.
- **As decisões dos ADRs viram critérios de aceite, não comentários**: o limite de 3 turnos (ADR-0002) é validação testável em T01; a regra de vigência (ADR-0003) é fixture obrigatória em T07; o corte de budget é teste em T08.
- **T01 responde `501` para input válido** enquanto o pipeline não existe — o endpoint nunca finge resposta, e o contrato fica utilizável pelo time do bot/painel desde o primeiro dia.

## 2. Implementação da T01 (com Claude Code)

Fluxo implementado: `request.json()` com guarda de JSON malformado → `validateQueryRequest` (Zod `safeParse`, nunca lança) → `400 INVALID_REQUEST` com `issues[{path, message}]` por violação, ou `501 PIPELINE_NOT_IMPLEMENTED` para input válido. Schemas `strict()` (campo desconhecido = 400), tipos inferidos via `z.infer`, registro `app.http` com `authLevel: "function"`.

**Verificação (rodada nesta máquina):**

```
✓ tests/unit/query-validator.test.ts (9 tests)
✓ tests/unit/query-handler.test.ts (3 tests)
Test Files  2 passed (2)   Tests  12 passed (12)

> tsc -p .   (build sem erros, strict: true)
```

Casos cobertos: body mínimo válido (+ default de histórico), 3 turnos no limite, `question` ausente/curta/longa, histórico acima de 6 mensagens, campo extra rejeitado, `sessionId` não-UUID, body não-objeto, JSON malformado, e os 3 fluxos do handler (501 válido / 400 inválido / 400 malformado).

## 3. Revisão crítica do código gerado (antes de um code review real)

Pontos **reais** identificados revisando o output do agente:

1. **`zod` estava em `devDependencies`** no `package.json` do scaffold e o código gerado importava sem reclassificar. Em produção (`npm ci --omit=dev` no deploy da Function) o endpoint quebraria no primeiro request. **Ajuste aplicado:** movido para `dependencies` junto com `@azure/functions`. É o tipo de erro silencioso que só estoura em deploy — checagem que vale automatizar no CI (`npm ls --omit=dev`).

2. **Logging fora do padrão do plan.** O handler usa `context.warn` (logger do host), mas o plan exige pino estruturado. Aceitável apenas porque T03 ainda não existe — porém o código gerado originalmente não deixava isso rastreável. **Ajuste aplicado:** `TODO(T11)`/referências às tasks no código; o ponto entraria no review como "dívida registrada, bloquear merge de T11 sem T03".

3. **Registro do trigger por efeito colateral de import** (`app.http(...)` no escopo do módulo). Funciona, mas: (a) importar o handler em teste dispara o registro (gera os warnings de "test mode" do `@azure/functions`); (b) com vários endpoints, a ordem/descoberta de imports vira acoplamento invisível. **Proposta:** extrair um `src/functions/index.ts` que centraliza os registros, deixando `handler.ts` puro (função testável sem side effects).

4. **Sem limite de tamanho do body antes do parse.** `request.json()` parseia qualquer payload que o host aceitar; um body de dezenas de MB consome memória/tempo antes do Zod rejeitar. **Proposta:** checar `Content-Length` (ex.: > 64KB → `413 PAYLOAD_TOO_LARGE`) antes do parse — entra como critério extra na T04/T11.

5. **`authLevel: "function"` é um chute do gerador, não uma decisão.** Para o bot do Teams e o painel web, a autenticação real provavelmente será outra (Azure AD / chave por serviço via APIM). O valor atual é seguro como default, mas **precisa de decisão registrada do Tech Lead** (candidata a ADR) antes do primeiro deploy — código gerado por IA tende a "resolver" decisões de segurança em silêncio; aqui o review deve devolvê-la para o humano.

**Conclusão da revisão:** itens 1–2 corrigidos/registrados nesta entrega; itens 3–5 viram comentários de review + ajustes nas tasks (T04/T11) e uma pauta de ADR para o TL.
