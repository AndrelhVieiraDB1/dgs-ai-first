# Evidência (extra) — Memória persistente de decisões e linguagem ubíqua

Server `memory` (reference server, grafo local persistido em `.mcp/memory.json`). Registra termos da linguagem ubíqua e decisões de ADR para reuso entre sessões dos agentes. Rodada de 2026-06-10.

---

## Server: `memory`

Comando: `npx -y @modelcontextprotocol/server-memory` (cwd: `/Users/andre.vieira/Downloads/novatech-assistant`)

Handshake OK — serverInfo: `{"name":"memory-server","version":"0.6.3"}`

### Registrar termos da linguagem ubíqua e decisão da ADR-0003

**Request (tools/call):**
```json
{
  "name": "create_entities",
  "arguments": {
    "entities": [
      {
        "name": "CT-e",
        "entityType": "termo-dominio",
        "observations": [
          "Conhecimento de Transporte Eletrônico — identificador obrigatório em chamados de devolução (POL-001 §3.3)."
        ]
      },
      {
        "name": "Tier de cliente",
        "entityType": "termo-dominio",
        "observations": [
          "Apenas Gold, Silver e Standard existem (SLA-2024 §1). Tier Platinum NÃO existe — alucinação comum."
        ]
      },
      {
        "name": "ADR-0003",
        "entityType": "decisao",
        "observations": [
          "Documentos contraditórios: metadado de vigência; priorizar versão mais recente (PROC-042 v2 sobre v1); obsoletos marcados, não excluídos."
        ]
      }
    ]
  }
}
```

**Response:**
```
[]
```

### Relacionar decisão e termo

**Request (tools/call):**
```json
{
  "name": "create_relations",
  "arguments": {
    "relations": [
      {
        "from": "ADR-0003",
        "to": "Tier de cliente",
        "relationType": "protege-contra-alucinacao-de"
      }
    ]
  }
}
```

**Response:**
```
[]
```

### Ler o grafo persistido (o que outro agente veria em nova sessão)

**Request (tools/call):**
```json
{
  "name": "read_graph",
  "arguments": {}
}
```

**Response:**
```
{
  "entities": [
    {
      "name": "CT-e",
      "entityType": "termo-dominio",
      "observations": [
        "Conhecimento de Transporte Eletrônico — identificador obrigatório em chamados de devolução (POL-001 §3.3)."
      ]
    },
    {
      "name": "Tier de cliente",
      "entityType": "termo-dominio",
      "observations": [
        "Apenas Gold, Silver e Standard existem (SLA-2024 §1). Tier Platinum NÃO existe — alucinação comum."
      ]
    },
    {
      "name": "ADR-0003",
      "entityType": "decisao",
      "observations": [
        "Documentos contraditórios: metadado de vigência; priorizar versão mais recente (PROC-042 v2 sobre v1); obsoletos marcados, não excluídos."
      ]
    }
  ],
  "relations": [
    {
      "from": "ADR-0003",
      "to": "Tier de cliente",
      "relationType": "protege-contra-alucinacao-de"
    }
  ]
}
```

