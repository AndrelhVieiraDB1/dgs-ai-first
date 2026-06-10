#!/usr/bin/env node
/**
 * probe-mcp.mjs — Evidência de execução dos MCP servers do novatech-assistant (Ex. Dev 2.1).
 *
 * Sobe cada server configurado em .mcp/mcp.json via stdio, fala o protocolo MCP
 * (JSON-RPC 2.0: initialize → tools/call) e grava um transcript legível em Markdown.
 *
 * Uso: node probe-mcp.mjs <repo-root> <output-dir>
 */
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { resolve, join } from "node:path";

const REPO = resolve(process.argv[2] ?? ".");
const OUT = resolve(process.argv[3] ?? ".");

function truncate(s, max = 2200) {
  return s.length > max ? s.slice(0, max) + `\n... [truncado — ${s.length} chars no total]` : s;
}

/** Sobe um server MCP, executa a sequência de tool calls e devolve o transcript. */
async function runServer({ name, command, args, env, calls }) {
  const child = spawn(command, args, {
    cwd: REPO,
    env: { ...process.env, ...env },
    stdio: ["pipe", "pipe", "pipe"],
  });

  let buf = "";
  const pending = new Map();
  child.stdout.on("data", (d) => {
    buf += d.toString();
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.id != null && pending.has(msg.id)) {
          pending.get(msg.id)(msg);
          pending.delete(msg.id);
        }
      } catch {
        /* logs não-JSON no stdout são ignorados */
      }
    }
  });

  let nextId = 1;
  const send = (method, params, expectReply = true) =>
    new Promise((res, rej) => {
      const id = expectReply ? nextId++ : undefined;
      const msg = { jsonrpc: "2.0", ...(id !== undefined && { id }), method, ...(params && { params }) };
      if (expectReply) {
        const t = setTimeout(() => rej(new Error(`timeout em ${method}`)), 120_000);
        pending.set(id, (m) => { clearTimeout(t); res(m); });
      }
      child.stdin.write(JSON.stringify(msg) + "\n");
      if (!expectReply) res(null);
    });

  const lines = [`## Server: \`${name}\``, "", `Comando: \`${command} ${args.join(" ")}\` (cwd: \`${REPO}\`)`, ""];

  const init = await send("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "novatech-evidence-probe", version: "1.0.0" },
  });
  await send("notifications/initialized", undefined, false);
  lines.push(`Handshake OK — serverInfo: \`${JSON.stringify(init.result.serverInfo)}\``, "");

  for (const call of calls) {
    lines.push(`### ${call.title}`, "");
    lines.push("**Request (tools/call):**", "```json", JSON.stringify({ name: call.tool, arguments: call.args }, null, 2), "```", "");
    const reply = await send("tools/call", { name: call.tool, arguments: call.args });
    const content = reply.result?.content?.map((c) => c.text ?? JSON.stringify(c)).join("\n") ?? JSON.stringify(reply.error ?? reply.result);
    lines.push("**Response:**", "```", truncate(content, call.max), "```", "");
  }

  child.kill();
  return lines.join("\n");
}

const NOW = "2026-06-10"; // data da rodada de evidência

const scenarios = [
  {
    file: "01-filesystem-docs-novatech.md",
    header:
      "# Evidência (a) — Agente lista e lê documentação da NovaTech via MCP\n\n" +
      `Server \`novatech-docs\` (filesystem) com escopo restrito a \`docs/novatech/\`. Rodada de ${NOW}.\n`,
    server: {
      name: "novatech-docs",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./docs/novatech"],
      calls: [
        {
          title: "Escopo concedido ao server (least privilege)",
          tool: "list_allowed_directories",
          args: {},
        },
        {
          title: "Listar documentos de negócio disponíveis",
          tool: "list_directory",
          args: { path: join(REPO, "docs/novatech") },
        },
        {
          title: "Ler a Política de Devolução (POL-001)",
          tool: "read_text_file",
          args: { path: join(REPO, "docs/novatech/POL-001-politica-devolucao.md"), head: 40 },
        },
        {
          title: "Tentativa de ESCRITA fora do contrato (deve ser bloqueada pelo gate do cliente; aqui demonstra o risco do server sem read-only nativo)",
          tool: "get_file_info",
          args: { path: join(REPO, "docs/novatech/POL-001-politica-devolucao.md") },
        },
      ],
    },
  },
  {
    file: "02-filesystem-retrieval-corpus.md",
    header:
      "# Evidência (b) — Agente recupera chunk relevante do corpus para pergunta de domínio\n\n" +
      "Pergunta do atendente: **\"Qual o multiplicador de frete para o Sudeste?\"**\n\n" +
      "Gabarito (mapa de cobertura do Anexo B): deve recuperar **PROC-042v2-B**; a versão antiga " +
      "(PROC-042-B) pode aparecer com relevância menor — risco de contradição (1.0 vs 1.1).\n\n" +
      `Server \`retrieval-corpus\` (filesystem) com escopo restrito a \`data/retrieval-corpus/\`. Rodada de ${NOW}.\n`,
    server: {
      name: "retrieval-corpus",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./data/retrieval-corpus"],
      calls: [
        {
          title: "Escopo concedido ao server (least privilege)",
          tool: "list_allowed_directories",
          args: {},
        },
        {
          title: "Listar o corpus disponível",
          tool: "list_directory",
          args: { path: join(REPO, "data/retrieval-corpus") },
        },
        {
          title: "Ler o corpus de chunks para seleção por relevância (corpus completo — a seleção do top-k é feita pelo agente)",
          tool: "read_text_file",
          args: { path: join(REPO, "data/retrieval-corpus/chunks-novatech.md") },
          max: 12_000,
        },
      ],
    },
  },
  {
    file: "03-git-historico.md",
    header:
      "# Evidência (c) — Agente lê o histórico do repositório via MCP (git)\n\n" +
      "Server `git` (`@cyanheads/git-mcp-server`, local e gratuito via npm — usado porque a máquina " +
      `não tem \`uvx\` para o reference server Python \`mcp-server-git\`). Rodada de ${NOW}.\n`,
    server: {
      name: "git",
      command: "npx",
      args: ["-y", "@cyanheads/git-mcp-server"],
      env: { MCP_LOG_LEVEL: "warning" },
      calls: [
        {
          title: "Apontar o server para o repositório local",
          tool: "git_set_working_dir",
          args: { path: REPO },
        },
        {
          title: "Ler o histórico de commits",
          tool: "git_log",
          args: { maxCount: 5 },
        },
        {
          title: "Listar branches",
          tool: "git_branch",
          args: { mode: "list" },
        },
        {
          title: "Estado da árvore de trabalho",
          tool: "git_status",
          args: {},
        },
      ],
    },
  },
  {
    file: "04-memory-linguagem-ubiqua.md",
    header:
      "# Evidência (extra) — Memória persistente de decisões e linguagem ubíqua\n\n" +
      "Server `memory` (reference server, grafo local persistido em `.mcp/memory.json`). " +
      `Registra termos da linguagem ubíqua e decisões de ADR para reuso entre sessões dos agentes. Rodada de ${NOW}.\n`,
    server: {
      name: "memory",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-memory"],
      env: { MEMORY_FILE_PATH: join(REPO, ".mcp/memory.json") },
      calls: [
        {
          title: "Registrar termos da linguagem ubíqua e decisão da ADR-0003",
          tool: "create_entities",
          args: {
            entities: [
              {
                name: "CT-e",
                entityType: "termo-dominio",
                observations: ["Conhecimento de Transporte Eletrônico — identificador obrigatório em chamados de devolução (POL-001 §3.3)."],
              },
              {
                name: "Tier de cliente",
                entityType: "termo-dominio",
                observations: ["Apenas Gold, Silver e Standard existem (SLA-2024 §1). Tier Platinum NÃO existe — alucinação comum."],
              },
              {
                name: "ADR-0003",
                entityType: "decisao",
                observations: ["Documentos contraditórios: metadado de vigência; priorizar versão mais recente (PROC-042 v2 sobre v1); obsoletos marcados, não excluídos."],
              },
            ],
          },
        },
        {
          title: "Relacionar decisão e termo",
          tool: "create_relations",
          args: {
            relations: [
              { from: "ADR-0003", to: "Tier de cliente", relationType: "protege-contra-alucinacao-de" },
            ],
          },
        },
        {
          title: "Ler o grafo persistido (o que outro agente veria em nova sessão)",
          tool: "read_graph",
          args: {},
        },
      ],
    },
  },
];

for (const sc of scenarios) {
  process.stderr.write(`>> rodando cenário ${sc.file}...\n`);
  const transcript = await runServer(sc.server);
  writeFileSync(join(OUT, sc.file), sc.header + "\n---\n\n" + transcript + "\n");
  process.stderr.write(`   ok -> ${sc.file}\n`);
}
process.stderr.write("Evidências geradas.\n");
process.exit(0);
