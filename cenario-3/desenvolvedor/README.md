# Cenário 3 — Fase de Governança e Validação · Entregáveis do DESENVOLVEDOR

| Exercício | Entregável | Arquivo |
|-----------|------------|---------|
| 3.1 — Structured output e verificações determinísticas | Schema Zod, response-validator, code review com correções, prompt × código | [dev-3.1-structured-output-harness.md](dev-3.1-structured-output-harness.md) |
| 3.2 — Revisão crítica de código gerado por IA | Revisão própria, revisão do Claude, comparação honesta, código reescrito | [dev-3.2-revisao-critica-codigo-ia.md](dev-3.2-revisao-critica-codigo-ia.md) |

Os artefatos de código vivem no repositório local `novatech-assistant`
(`~/Downloads/novatech-assistant`), commit desta fase:

- `src/shared/types.ts` (`assistantResponseSchema` — structured output) — Ex. 3.1
- `src/services/response-validator.ts` + `tests/unit/response-validator.test.ts` (21 testes) — Ex. 3.1
- `src/functions/feedback/{validator,store,handler}.ts` + testes (11 casos) — Ex. 3.2
- `src/shared/logger.ts` (redact de `attendantEmail`/`email`) e `src/shared/config.ts` (`getCosmosConfig` fail-fast) — Ex. 3.2
- Suíte completa: **54 testes ✅**, `tsc` strict ✅
