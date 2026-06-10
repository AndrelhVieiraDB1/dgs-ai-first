# Cenário 2 — Fase de Estruturação · Entregáveis do DESENVOLVEDOR

| Exercício | Entregável | Arquivo |
|-----------|------------|---------|
| 2.1 — MCP servers | Mapeamento, `.mcp/mcp.json`, least privilege, riscos | [dev-2.1-mcp-servers.md](dev-2.1-mcp-servers.md) |
| 2.1 — Evidência de execução | Transcripts JSON-RPC reais dos servers + script reproduzível | [evidencias-mcp/](evidencias-mcp/) |
| 2.2 — SDD | tasks.md, implementação da T01, revisão crítica | [dev-2.2-sdd-query-endpoint.md](dev-2.2-sdd-query-endpoint.md) |
| 2.3 — Skills | Árvore de skills, mapeamento criação/consumo, SKILL.md Foundation | [dev-2.3-estrategia-skills.md](dev-2.3-estrategia-skills.md) |

Os artefatos de código vivem no repositório local `novatech-assistant`
(`~/Downloads/novatech-assistant`), commits desta fase:

- `.mcp/mcp.json` (schema puro) + `.mcp/README.md` (justificativa de escopos) + `.claude/settings.json` (gate de escrita read-only) — Ex. 2.1
- `specs/query-endpoint/plan.md` e `tasks.md` — Ex. 2.2
- `src/shared/{types,config,logger}.ts`, `src/functions/query/{validator,handler}.ts`, `tests/unit/*` (T01–T03: 21 testes ✅, `tsc` strict ✅) — Ex. 2.2
- `skills/foundation/typescript-conventions.md` — Ex. 2.3
