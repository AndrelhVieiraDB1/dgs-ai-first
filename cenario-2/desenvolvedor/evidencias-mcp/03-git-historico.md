# Evidência (c) — Agente lê o histórico do repositório via MCP (git)

Server `git` (`@cyanheads/git-mcp-server`, local e gratuito via npm — usado porque a máquina não tem `uvx` para o reference server Python `mcp-server-git`). Rodada de 2026-06-10.

---

## Server: `git`

Comando: `npx -y @cyanheads/git-mcp-server` (cwd: `/Users/andre.vieira/Downloads/novatech-assistant`)

Handshake OK — serverInfo: `{"name":"@cyanheads/git-mcp-server","version":"2.15.1"}`

### Apontar o server para o repositório local

**Request (tools/call):**
```json
{
  "name": "git_set_working_dir",
  "arguments": {
    "path": "/Users/andre.vieira/Downloads/novatech-assistant"
  }
}
```

**Response:**
```
{
  "success": true,
  "path": "/Users/andre.vieira/Downloads/novatech-assistant",
  "message": "Working directory set to: /Users/andre.vieira/Downloads/novatech-assistant",
  "repository": {
    "status": {
      "branch": "master",
      "isClean": false,
      "staged": [],
      "unstaged": [
        ".gitignore",
        ".mcp/mcp.json"
      ],
      "untracked": [
        ".claude/"
      ],
      "conflicts": []
    },
    "recentCommits": [
      {
        "hash": "bbdd03a",
        "author": "Trilha AI First",
        "date": "2026-06-09T18:13:30.000Z",
        "subject": "chore: starter repo (Anexo D) — estrutura + dados semeados dos Anexos A e B"
      }
    ],
    "recentTags": [],
    "remotes": []
  }
}
```

### Ler o histórico de commits

**Request (tools/call):**
```json
{
  "name": "git_log",
  "arguments": {
    "maxCount": 5
  }
}
```

**Response:**
```
{
  "success": true,
  "commits": [
    {
      "hash": "bbdd03aeecd7e349a2bfc93849e0552a0b766ac6",
      "shortHash": "bbdd03a",
      "author": "Trilha AI First",
      "authorEmail": "trilha@db1.local",
      "timestamp": 1781028810,
      "subject": "chore: starter repo (Anexo D) — estrutura + dados semeados dos Anexos A e B",
      "parents": []
    }
  ],
  "totalCount": 1
}
```

### Listar branches

**Request (tools/call):**
```json
{
  "name": "git_branch",
  "arguments": {
    "mode": "list"
  }
}
```

**Response:**
```
{
  "success": true,
  "mode": "list",
  "branches": [
    {
      "name": "master",
      "commitHash": "bbdd03aeecd7e349a2bfc93849e0552a0b766ac6",
      "current": true,
      "ahead": 0,
      "behind": 0
    }
  ],
  "currentBranch": "master",
  "message": null
}
```

### Estado da árvore de trabalho

**Request (tools/call):**
```json
{
  "name": "git_status",
  "arguments": {}
}
```

**Response:**
```
{
  "success": true,
  "currentBranch": "master",
  "isClean": false,
  "stagedChanges": {},
  "unstagedChanges": {
    "modified": [
      ".gitignore",
      ".mcp/mcp.json"
    ]
  },
  "untrackedFiles": [
    ".claude/"
  ],
  "conflictedFiles": []
}
```

