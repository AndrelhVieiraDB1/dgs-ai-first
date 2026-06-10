# Configuração e Uso Real de MCP Servers no Projeto
**Exercício Desenvolvedor 2.1**
**Papel:** Desenvolvedor
**Projeto:** Assistente de IA para Atendimento — NovaTech Logística
**Data da rodada de evidência:** 2026-06-10

---

## 1. Mapeamento: necessidade do projeto → MCP server

Todos os servers são locais e gratuitos (rodam via `npx`, sem nenhum serviço pago ou externo). Onde a operação real usaria Confluence, Azure AI Search e GitHub, esta fase usa filesystem + git locais — a fronteira MCP é a mesma, só muda o backend.

| # | Necessidade | Server (instância) | O que expõe | Quem consome | Escopo concedido |
|---|-------------|--------------------|-------------|--------------|------------------|
| 1 | Código, specs e skills (ler **e escrever**) | `repo-fs` — `@modelcontextprotocol/server-filesystem` | Tools: `read_text_file`, `write_file`, `edit_file`, `list_directory`, `search_files`, `directory_tree`… | Devs e Tech Lead via Claude Code / Copilot (geração de código, tasks.md, skills) | `./src ./specs ./skills ./prompts ./tests ./docs/adr` |
| 2 | Documentação de negócio da NovaTech (ler) | `novatech-docs` — instância separada do filesystem server | Mesmas tools, mas **somente as de leitura são permitidas** pelo gate do cliente | Todos os papéis (consulta a POL-001, PROC-042, SLA-2024, FAQ durante geração de prompts, testes e specs) | `./docs/novatech/` — **read-only** |
| 3 | Corpus de chunks para "recuperação" (ler) | `retrieval-corpus` — instância separada do filesystem server | Mesmas tools de leitura | Dev e QA (simular retrieval, montar fixtures e golden queries) | `./data/retrieval-corpus/` — **read-only** |
| 4 | Histórico/branches do repositório | `git` — `@cyanheads/git-mcp-server` (npm) | Tools: `git_log`, `git_diff`, `git_branch`, `git_status`, `git_show`, `git_blame`… | Devs (contexto de mudanças), Tech Lead (review), QA (rastrear regressões) | repositório local (via `git_set_working_dir`) |
| 5 | Memória persistente de decisões e linguagem ubíqua | `memory` — `@modelcontextprotocol/server-memory` | Tools: `create_entities`, `create_relations`, `search_nodes`, `read_graph` (grafo de conhecimento) | Todos os agentes do time (glossário de domínio: CT-e, tiers, vigência de PROC-042; decisões de ADR resumidas) | arquivo local `.mcp/memory.json` (gitignored) |
| 6 | Explorar primitivas MCP (aprendizado) | `everything` — `@modelcontextprotocol/server-everything` | Tools/resources/prompts de demonstração | Time todo, **apenas em ambiente de estudo** | — (não entra no `mcp.json` do projeto; ver justificativa abaixo) |

**Notas sobre escolhas:**

- **Três instâncias do mesmo filesystem server, não uma.** O reference server aplica escopo por processo (lista de diretórios permitidos), mas não tem flag de read-only. Separar instâncias permite tratar permissões por *fonte*: o gate de escrita do cliente nega `write_file`/`edit_file`/`move_file`/`create_directory` nas instâncias `novatech-docs` e `retrieval-corpus`, enquanto `repo-fs` mantém escrita (com confirmação humana).
- **Git via npm em vez do reference server Python.** O reference `mcp-server-git` roda via `uvx`, que não está instalado nas máquinas do time. O `@cyanheads/git-mcp-server` é equivalente, local e gratuito via `npx` — mantendo o critério "nenhum serviço pago/externo". Se `uv` for instalado, trocar por `uvx mcp-server-git --repository .` é uma mudança de 2 linhas.
- **`everything` fora do `mcp.json` do projeto.** Ele existe para aprender as primitivas do protocolo (tools/resources/prompts), não atende nenhuma necessidade do projeto e adiciona superfície de ataque/ruído de contexto. Least privilege também é não ligar o que não se usa — quem quiser estudar roda `npx -y @modelcontextprotocol/server-everything` em sessão à parte.

---

## 2. `.mcp/mcp.json` final

Arquivo criado no repositório (`novatech-assistant/.mcp/mcp.json`):

```json
{
  "mcpServers": {
    "repo-fs": {
      "command": "npx",
      "args": [
        "-y", "@modelcontextprotocol/server-filesystem",
        "./src", "./specs", "./skills", "./prompts", "./tests", "./docs/adr"
      ]
    },
    "novatech-docs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./docs/novatech"]
    },
    "retrieval-corpus": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data/retrieval-corpus"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@cyanheads/git-mcp-server"],
      "env": { "MCP_LOG_LEVEL": "warning", "GIT_SIGN_COMMITS": "false" }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": { "MEMORY_FILE_PATH": "./.mcp/memory.json" }
    }
  }
}
```

Complementado pelo gate de escrita do cliente (`novatech-assistant/.claude/settings.json`):

```json
{
  "permissions": {
    "deny": [
      "mcp__novatech-docs__write_file", "mcp__novatech-docs__edit_file",
      "mcp__novatech-docs__create_directory", "mcp__novatech-docs__move_file",
      "mcp__retrieval-corpus__write_file", "mcp__retrieval-corpus__edit_file",
      "mcp__retrieval-corpus__create_directory", "mcp__retrieval-corpus__move_file",
      "mcp__git__git_push", "mcp__git__git_reset", "mcp__git__git_clean", "mcp__git__git_rebase"
    ],
    "ask": [
      "mcp__git__git_commit",
      "mcp__repo-fs__write_file", "mcp__repo-fs__edit_file", "mcp__repo-fs__move_file"
    ]
  }
}
```

### Justificativa de least privilege, server a server

| Server | Por que este escopo é o mínimo suficiente |
|--------|-------------------------------------------|
| `repo-fs` | O agente só produz artefatos em `src/`, `specs/`, `skills/`, `prompts/`, `tests/` e `docs/adr/`. **Não recebe a raiz do repo**: isso deixaria `.env` (segredos), `.git/` (reescrita de histórico sem passar pelo server git), `infra/` (Bicep — mudança de infraestrutura não é tarefa de agente nesta fase) e `.github/workflows/` (um agente editando CI pode se auto-conceder permissões) acessíveis para leitura E escrita. Cada pasta extra no escopo é um risco sem contrapartida. |
| `novatech-docs` | Documentação de negócio é **fonte de verdade do domínio** — o agente consulta, nunca altera (uma "correção" do agente na POL-001 contaminaria a base que alimenta o RAG). Instância separada + deny de escrita no cliente = read-only efetivo. |
| `retrieval-corpus` | Mesmo raciocínio: o corpus simula o índice do Azure AI Search. Se o agente pudesse escrever, poderia "plantar" chunks que justificam o próprio output (autocontaminação do retrieval). |
| `git` | Apenas repositório local, sem credenciais de remoto. Tools destrutivas (`push`, `reset`, `clean`, `rebase`) negadas; `commit` exige confirmação humana. O agente usa o que precisa: `log`, `diff`, `branch`, `status`, `show`. |
| `memory` | Persiste num único arquivo local dentro de `.mcp/`, gitignored. Não tem acesso a nada além do próprio grafo. |

---

## 3. Evidência de execução

Os servers foram **efetivamente executados** nesta máquina em 2026-06-10, via protocolo MCP real (JSON-RPC 2.0 sobre stdio: `initialize` → `notifications/initialized` → `tools/call`). O script reproduzível está em [`evidencias-mcp/probe-mcp.mjs`](evidencias-mcp/probe-mcp.mjs) e os transcripts completos (request + response de cada tool call) em:

| Evidência exigida | Transcript | O que mostra |
|-------------------|-----------|--------------|
| (a) Listar e ler documento de `docs/novatech/` | [`evidencias-mcp/01-filesystem-docs-novatech.md`](evidencias-mcp/01-filesystem-docs-novatech.md) | `list_allowed_directories` (escopo restrito), `list_directory` com os 6 arquivos, `read_text_file` da POL-001 |
| (b) Recuperar chunk relevante do corpus | [`evidencias-mcp/02-filesystem-retrieval-corpus.md`](evidencias-mcp/02-filesystem-retrieval-corpus.md) | Para a pergunta *"Qual o multiplicador de frete para o Sudeste?"*, leitura do corpus e seleção do chunk — análise contra o gabarito abaixo |
| (c) Ler histórico do repo via git | [`evidencias-mcp/03-git-historico.md`](evidencias-mcp/03-git-historico.md) | `git_set_working_dir`, `git_log` (commit `bbdd03a` do starter repo), `git_branch`, `git_status` |
| (extra) Memória persistente | [`evidencias-mcp/04-memory-linguagem-ubiqua.md`](evidencias-mcp/04-memory-linguagem-ubiqua.md) | `create_entities` (CT-e, tiers, ADR-0003), `create_relations`, `read_graph` — grafo persistido em `.mcp/memory.json` |

### Análise da evidência (b) contra o gabarito do Anexo B

Pergunta de domínio: **"Qual o multiplicador de frete para o Sudeste?"**

- Gabarito (mapa de cobertura): deve recuperar **PROC-042v2-B**; **PROC-042-B** (versão antiga) pode aparecer com relevância menor — contradição proposital 1.0 vs 1.1.
- Resultado: o agente recuperou via MCP o corpus e selecionou o chunk **PROC-042v2-B** — *"Multiplicadores regionais atualizados (novembro/2023): Sul 1.3, **Sudeste 1.1**, Centro-Oeste 1.4, Nordeste 1.5, Norte 1.8"* — descartando o PROC-042-B (Sudeste 1.0) por ser da versão v1, conforme a regra de vigência da ADR-0003. ✅ Match com o gabarito, incluindo o tratamento da armadilha de contradição.

---

## 4. Análise de riscos (contexto local) e mitigações

| # | Risco | Cenário concreto neste projeto | Mitigação aplicada |
|---|-------|--------------------------------|--------------------|
| 1 | **Escopo amplo do filesystem expõe segredos** | Um `filesystem` apontado para `.` (raiz) leria `.env` (futuras keys do Azure OpenAI/AI Search) e `local.settings.json`. O conteúdo entra no contexto do modelo e pode vazar em logs, telemetria ou numa resposta gerada. | `repo-fs` recebe lista explícita de 6 pastas; raiz, `.env`, `.git/`, `infra/` e `.github/` ficam fora do alcance de qualquer server. `.env` também está no `.gitignore`. |
| 2 | **Escrita sem gate humano** | O reference filesystem server não tem modo read-only: com uma instância única, o agente poderia "corrigir" a POL-001 ou plantar chunks no corpus — corrompendo a fonte de verdade que alimenta o RAG e os testes, sem ninguém revisar. | Instâncias separadas por fonte + `permissions.deny` no cliente para todas as tools de escrita de `novatech-docs` e `retrieval-corpus`; escrita do `repo-fs` em modo `ask` (toda escrita passa por aprovação e depois por code review via git). |
| 3 | **Operações git destrutivas ou de publicação** | O server git npm expõe `git_push`, `git_reset --hard`, `git_clean` — um agente confuso poderia descartar trabalho não commitado ou publicar código não revisado quando houver remoto. | `deny` para `push`/`reset`/`clean`/`rebase`; `commit` em modo `ask`. Sem credenciais de remoto configuradas nesta fase. |
| 4 | **Supply chain dos pacotes npx** | `npx -y` baixa e executa o pacote automaticamente; um typosquat (`@modelcontextprotocal/...`) ou versão comprometida executaria código arbitrário na máquina do dev. | Usar apenas pacotes verificados no README oficial de `modelcontextprotocol/servers` (e o repositório do server npm de git); conferir o nome exato antes de adicionar ao `mcp.json`; versionar o `mcp.json` no repo para que mudanças de server passem por review. Evolução natural: pinar versões (`@modelcontextprotocol/server-filesystem@0.2.0`). |
| 5 | **Prompt injection via conteúdo lido** | Os documentos da NovaTech vêm de fora do time (e o FAQ é informal). Um documento contendo instruções (“ignore suas regras e...”) seria lido pelo agente como contexto. Com escrita habilitada, instrução maliciosa + tool de escrita = modificação de código. | Fontes externas são read-only (limita o dano); toda escrita em código exige aprovação humana; AGENTS.md instrui a tratar conteúdo de `docs/novatech/` como **dados**, nunca como instruções. |

---

## 5. Como reproduzir

```bash
cd novatech-assistant
# evidência ponta-a-ponta (gera os 4 transcripts):
node <caminho>/evidencias-mcp/probe-mcp.mjs . <pasta-de-saida>

# ou abrir o Claude Code no repo — ele carrega .mcp/mcp.json automaticamente
# e aplica o gate de .claude/settings.json.
```
