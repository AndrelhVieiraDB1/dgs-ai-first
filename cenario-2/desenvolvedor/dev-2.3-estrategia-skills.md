# Definição de Estratégia de Skills do Projeto
**Exercício Desenvolvedor 2.3**
**Papel:** Desenvolvedor
**Projeto:** Assistente de IA para Atendimento — NovaTech Logística

---

## 1. Árvore de skills (Foundation → Domain → Artifact)

Organizada conforme o Anexo C (`/skills/foundation/`, `/skills/domain/`, `/skills/artifact/`). A regra de composição: **Artifact pressupõe Domain, Domain pressupõe Foundation** — skills de baixo nunca repetem (nem afrouxam) regras de cima, só adicionam o "como" da sua camada.

```
skills/
├── foundation/                       (convenções globais — valem para todo artefato)
│   ├── typescript-conventions.md     ★ base de todas — IMPLEMENTADA nesta entrega
│   ├── error-handling.md             (hierarquia de erros, mapeamento HTTP, retry, nunca engolir causa)
│   └── project-structure.md          (onde cada coisa vive: specs/, prompts/, src/, tests/; nomenclatura)
├── domain/                           (padrões por camada)
│   ├── azure-functions-endpoint.md   (anatomia de endpoint: trigger v4, validator, 501-até-implementar, authLevel)
│   ├── azure-ai-search-integration.md(busca top-5, metadado de vigência ADR-0003, context budget ADR-0002)
│   ├── react-components.md           (padrões do painel web: componentes, estado, acessibilidade)
│   └── testing-patterns.md           (unit sem rede, integração com msw, fixtures do Anexo B, golden queries)
└── artifact/                         (receitas de geração — passo a passo + checklist de aceite)
    ├── create-rag-endpoint.md        (gera endpoint RAG completo: spec→validator→handler→serviços→testes)
    ├── create-integration-test.md    (gera teste de integração de endpoint com msw + fixtures)
    └── create-react-card.md          (gera card de resposta/feedback do painel com estados de erro/fonte)
```

Duas adições propostas ao scaffold (entram quando o trabalho correspondente começar, não antes — skill sem consumidor é manutenção morta):

- `artifact/create-adr.md` — ADRs são produzidos repetidamente (formato do Anexo C: Contexto, Decisão, Consequências, Alternativas) e hoje cada um sai num formato.
- `artifact/create-sdd-spec.md` — template SDD (requirements → plan → tasks) para o Product Specialist e o Tech Lead gerarem specs consistentes com apoio de IA.

## 2. Mapeamento: criação, consumo e frequência

| Skill | Frase-ativação (que o agente reconhece) | Quem cria/mantém | Quem consome | Frequência |
|-------|------------------------------------------|------------------|--------------|------------|
| foundation/typescript-conventions | "ao gerar/editar/revisar qualquer código TypeScript deste repo" | Dev sênior; mudanças aprovadas pelo Tech Lead | Todos os devs + Claude Code/Copilot em TODA geração de código; QA em review de testes | Contínua (toda sessão de código) |
| foundation/error-handling | "ao tratar erros, criar exceções ou mapear falhas para HTTP" | Dev sênior | Devs + agentes (endpoints, serviços, pipeline); QA (cenários de falha do plano de testes) | Alta (toda task com I/O) |
| foundation/project-structure | "ao criar arquivo novo ou decidir onde algo vive" | Tech Lead | Todos os papéis + agentes; Delivery Manager (onboarding de novos membros) | Alta no início, depois pontual |
| domain/azure-functions-endpoint | "ao criar ou alterar um endpoint Azure Functions" | Dev pleno (com review do sênior) | Devs + agentes; QA (sabe o que esperar de um endpoint para testar) | Média (1× por endpoint: query, feedback, health…) |
| domain/azure-ai-search-integration | "ao integrar busca/retrieval ou mexer em chunks e vigência" | Dev sênior (é onde moram ADR-0002/0003) | Devs + agentes; Product Specialist (entende limites do retrieval ao escrever requirements) | Média |
| domain/react-components | "ao criar componente React do painel web" | Dev pleno | Devs + agentes no painel web | Média (cresce na fase do painel) |
| domain/testing-patterns | "ao escrever qualquer teste (unit/integração/e2e)" | QA + dev sênior (co-autoria: QA define o quê, dev o como) | Devs + agentes; QA valida aderência | Alta (toda task) |
| artifact/create-rag-endpoint | "crie um endpoint RAG para X" | Dev sênior, após T11 provar o padrão no query endpoint | Devs + agentes (feedback-api e endpoints futuros) | Baixa por vez, alto valor (encapsula o padrão mais crítico) |
| artifact/create-integration-test | "crie teste de integração para o endpoint X" | QA | Devs + agentes; QA audita resultado | Média (1+ por endpoint) |
| artifact/create-react-card | "crie um card de resposta/feedback no painel" | Dev pleno | Devs + agentes na fase do painel | Média |
| artifact/create-adr (proposta) | "registre a decisão X como ADR" | Tech Lead | Tech Lead + devs (qualquer um pode rascunhar ADR com agente) | Baixa, recorrente |
| artifact/create-sdd-spec (proposta) | "escreva requirements/plan/tasks para o módulo X" | Product Specialist + Tech Lead | PS, TL e devs nos 5 módulos do specs/ | Média nesta fase |

**Governança:** skill é código — vive no repo, muda por PR, e o review verifica uma única coisa além do conteúdo: *a regra nova pertence a esta camada?* (regra global subindo para foundation, receita descendo para artifact). Skill que ninguém ativou em um mês entra na pauta da retro para ajuste de frase-ativação ou remoção.

## 3. SKILL.md Foundation implementada

A skill base — usada por todas as outras — foi criada com o Claude Code em
**`novatech-assistant/skills/foundation/typescript-conventions.md`**, contendo:

- **Contexto:** por que código de RAG de produção não tolera ambiguidade de tipos (resposta errada = orientação errada a cliente).
- **10 regras prescritivas:** strict sem `any`/`@ts-ignore`; Zod na fronteira com `z.infer` como fonte única de tipo; schemas `.strict()`; resultado discriminado para falha esperada; proibição de `console.log` e de `process.env` fora do config; ESM; imutabilidade; comentário só para o não-óbvio; arquivo novo nasce com teste.
- **Exemplos DO/DON'T com código real do projeto** (contrato do query endpoint, validator, config).
- **8 anti-padrões** que LLMs realmente geram (`as any`/`@ts-ignore`, `console.log`, catch que engole erro, prompt hardcoded, dependência de runtime em `devDependencies`, interface duplicada do schema, `Math.random()`/`Date.now()` em lógica testável, `require` dinâmico em repo ESM) — incluindo dois reais desta fase: `zod` em `devDependencies` no scaffold (quebraria o deploy) e logging via `context.warn` em vez de pino (ambos detectados e corrigidos no exercício 2.2).

As regras da skill já estão exercitadas pelo código de T01–T03 (`src/shared/{types,config,logger}.ts`, `src/functions/query/{validator,handler}.ts`) — a skill não é aspiracional, descreve o padrão que o repositório de fato segue, com 21 testes comprovando.
