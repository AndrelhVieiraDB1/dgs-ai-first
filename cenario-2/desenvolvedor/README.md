# Cenário 2 — Fase de Estruturação · Entregáveis do DESENVOLVEDOR

| Exercício | Entregável | Arquivo |
|-----------|------------|---------|
| 2.1 — MCP servers | Mapeamento, `.mcp/mcp.json`, least privilege, riscos | [dev-2.1-mcp-servers.md](dev-2.1-mcp-servers.md) |
| 2.1 — Evidência de execução | Transcripts JSON-RPC reais dos servers + script reproduzível | [evidencias-mcp/](evidencias-mcp/) |
| 2.2 — SDD | tasks.md, implementação da T01, revisão crítica | [dev-2.2-sdd-query-endpoint.md](dev-2.2-sdd-query-endpoint.md) |
| 2.3 — Skills | Árvore de skills, mapeamento criação/consumo, SKILL.md Foundation | [dev-2.3-estrategia-skills.md](dev-2.3-estrategia-skills.md) |

Os artefatos de código vivem no repositório local `novatech-assistant`
(`~/Downloads/novatech-assistant`), commit desta fase:

- `.mcp/mcp.json` + `.claude/settings.json` (gate de escrita) — Ex. 2.1
- `specs/query-endpoint/plan.md` e `tasks.md` — Ex. 2.2
- `src/shared/types.ts`, `src/functions/query/{validator,handler}.ts`, `tests/unit/*` (12 testes ✅, `tsc` ✅) — Ex. 2.2 (T01)
- `skills/foundation/typescript-conventions.md` — Ex. 2.3
