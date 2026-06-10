# Evidência (a) — Agente lista e lê documentação da NovaTech via MCP

Server `novatech-docs` (filesystem) com escopo restrito a `docs/novatech/`. Rodada de 2026-06-10.

---

## Server: `novatech-docs`

Comando: `npx -y @modelcontextprotocol/server-filesystem ./docs/novatech` (cwd: `/Users/andre.vieira/Downloads/novatech-assistant`)

Handshake OK — serverInfo: `{"name":"secure-filesystem-server","version":"0.2.0"}`

### Escopo concedido ao server (least privilege)

**Request (tools/call):**
```json
{
  "name": "list_allowed_directories",
  "arguments": {}
}
```

**Response:**
```
Allowed directories:
/Users/andre.vieira/Downloads/novatech-assistant/docs/novatech
```

### Listar documentos de negócio disponíveis

**Request (tools/call):**
```json
{
  "name": "list_directory",
  "arguments": {
    "path": "/Users/andre.vieira/Downloads/novatech-assistant/docs/novatech"
  }
}
```

**Response:**
```
[FILE] FAQ-atendimento.md
[FILE] POL-001-politica-devolucao.md
[FILE] PROC-042-frete-especial-v1.md
[FILE] PROC-042-v2-frete-especial-revisado.md
[FILE] README.md
[FILE] SLA-2024-tabela-sla-clientes.md
```

### Ler a Política de Devolução (POL-001)

**Request (tools/call):**
```json
{
  "name": "read_text_file",
  "arguments": {
    "path": "/Users/andre.vieira/Downloads/novatech-assistant/docs/novatech/POL-001-politica-devolucao.md",
    "head": 40
  }
}
```

**Response:**
```
# POL-001 — Política de Devolução de Mercadorias

**Versão:** 3.1
**Última atualização:** 15/01/2024
**Responsável:** Diretoria de Operações
**Classificação:** Documento normativo — uso obrigatório pelo time de atendimento

## 1. Objetivo

Esta política define as regras e procedimentos para devolução de mercadorias transportadas pela NovaTech, aplicável a todos os tipos de cliente e categorias de carga, salvo exceções explicitamente listadas na seção 3.

## 2. Escopo

Aplica-se a todas as devoluções solicitadas por clientes da NovaTech após a entrega da mercadoria. Não se aplica a mercadorias ainda em trânsito (para essas, consultar PROC-088: Procedimento de Interceptação de Carga).

## 3. Regras de Devolução

### 3.1. Prazo geral

O cliente pode solicitar a devolução de mercadorias em até 7 (sete) dias úteis após a data de recebimento confirmada no sistema de tracking. A contagem de dias úteis exclui sábados, domingos e feriados nacionais.

### 3.2. Exceções ao prazo geral

As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão:

- Cargas perigosas classificadas nas classes 1 a 6 da ANTT (Agência Nacional de Transportes Terrestres), conforme Resolução ANTT nº 5.947/2021. Inclui: explosivos (classe 1), gases (classe 2), líquidos inflamáveis (classe 3), sólidos inflamáveis (classe 4), oxidantes e peróxidos (classe 5), substâncias tóxicas e infectantes (classe 6).
- Cargas refrigeradas que tenham rompido a cadeia de frio (temperatura fora da faixa especificada na nota fiscal por mais de 30 minutos contínuos, conforme registro do sensor IoT).
- Cargas com lacre de segurança violado, salvo quando a violação for documentada no ato de entrega com assinatura do motorista e do recebedor.

Para essas categorias, o cliente deve entrar em contato com o setor de Gestão de Riscos (ramal 4500) para tratamento individual.

### 3.3. Procedimento de devolução

1. O cliente abre chamado no Portal do Cliente (portal.novatech.com.br), selecionando a categoria "Devolução de Mercadoria".
2. O chamado deve incluir: número do CT-e (Conhecimento de Transporte Eletrônico), fotos da mercadoria no estado atual (mínimo 3 fotos: embalagem externa, etiqueta de 
... [truncado — 2605 chars no total]
```

### Tentativa de ESCRITA fora do contrato (deve ser bloqueada pelo gate do cliente; aqui demonstra o risco do server sem read-only nativo)

**Request (tools/call):**
```json
{
  "name": "get_file_info",
  "arguments": {
    "path": "/Users/andre.vieira/Downloads/novatech-assistant/docs/novatech/POL-001-politica-devolucao.md"
  }
}
```

**Response:**
```
size: 3394
created: Tue Jun 09 2026 15:12:41 GMT-0300 (Brasilia Standard Time)
modified: Tue Jun 09 2026 15:12:41 GMT-0300 (Brasilia Standard Time)
accessed: Wed Jun 10 2026 18:46:01 GMT-0300 (Brasilia Standard Time)
isDirectory: false
isFile: true
permissions: 644
```

