"""
pipeline.py — Pipeline de RAG para NovaTech (PoC)
Exercício Desenvolvedor 1.3

Stack:
  - Chunking   : por seção semântica (headings Markdown) com overlap de parágrafo
  - Embeddings : TF-IDF vetorial puro Python (sem deps de ML pesadas)
  - Vector store: ChromaDB local (persistência em ./chroma_db) com embeddings manuais
  - Retrieval  : cosine similarity sobre vetores TF-IDF com boosts por tipo de doc
  - Geração    : prompt montado — colar no Claude/ChatGPT manualmente

Decisão de design — por que TF-IDF em vez de all-MiniLM-L6-v2?
  O CDN de modelos ONNX do ChromaDB não está acessível neste ambiente.
  TF-IDF é transparente, inspecionável e funciona bem em domínio fechado onde
  os termos são altamente discriminativos (PROC-042, CT-e, Gold, ANTT, etc.).
  Em produção Azure: substituir por text-embedding-ada-002 ou all-MiniLM via API.
"""

import os, re, math, json
from collections import Counter
from typing import List, Dict, Tuple, Optional
import chromadb

# ─────────────────────────────────────────────
# METADADOS DE VERSÃO
# ─────────────────────────────────────────────
DOC_METADATA = {
    "POL-001-politica-devolucao.md":          {"doc_id": "POL-001",     "version": "3.1",     "date": "2024-01-15", "type": "normativo"},
    "PROC-042-frete-especial-v1.md":          {"doc_id": "PROC-042-v1", "version": "1.0",     "date": "2023-03-03", "type": "normativo"},
    "PROC-042-v2-frete-especial-revisado.md": {"doc_id": "PROC-042-v2", "version": "2.0",     "date": "2023-11-10", "type": "normativo"},
    "SLA-2024-tabela-sla-clientes.md":        {"doc_id": "SLA-2024",    "version": "2024.1",  "date": "2024-01-02", "type": "contratual"},
    "FAQ-atendimento.md":                     {"doc_id": "FAQ",          "version": "informal","date": "2024-01-01", "type": "informal"},
}
CONFLICTING_PAIRS = [("PROC-042-v1", "PROC-042-v2")]


# ─────────────────────────────────────────────
# 1. TF-IDF ENGINE
# ─────────────────────────────────────────────

STOPWORDS_PT = {"a","o","e","de","do","da","para","em","com","que","se","um",
                "uma","os","as","no","na","por","ao","são","tem","não","mais",
                "já","ou","é","foi","ser","ter","seu","sua","este","esta",
                "isso","aqui","quando","como","mas","então","também","entre"}

def tokenize(text: str) -> List[str]:
    tokens = re.findall(r'\b[A-Za-záéíóúàãõâêîôûçÁÉÍÓÚÀÃÕÂÊÎÔÛÇ0-9][A-Za-záéíóúàãõâêîôûçÁÉÍÓÚÀÃÕÂÊÎÔÛÇ0-9\-]*\b', text)
    return [t.lower() for t in tokens if t.lower() not in STOPWORDS_PT and len(t) > 1]

def build_vocab_and_idf(all_texts: List[str]) -> Dict[str, float]:
    N = len(all_texts)
    df: Counter = Counter()
    for text in all_texts:
        for term in set(tokenize(text)):
            df[term] += 1
    return {term: math.log((N + 1) / (cnt + 1)) + 1.0 for term, cnt in df.items()}

def tfidf_vector(text: str, idf: Dict[str, float], vocab: List[str]) -> List[float]:
    tf = Counter(tokenize(text))
    total = sum(tf.values()) or 1
    return [tf.get(term, 0) / total * idf.get(term, 1.0) for term in vocab]

def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x**2 for x in a))
    nb = math.sqrt(sum(y**2 for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ─────────────────────────────────────────────
# 2. CHUNKING
# ─────────────────────────────────────────────

def chunk_document(text: str, meta: dict, filename: str) -> List[Dict]:
    """
    Estratégia: heading semântico (## / ###) como fronteira de chunk.

    Justificativa para NÃO usar 512 tokens fixo:
    - Tabelas de multiplicadores cabem em ~80 tokens mas respondem uma classe
      inteira de perguntas. Cortar no meio de uma tabela = resposta errada.
    - Atendentes perguntam por seção ("qual o SLA do Gold?") → mapeamento 1:1.
    - Overlap: último parágrafo da seção anterior é copiado como prefixo para
      preservar contexto em fronteiras (ex: regra anunciada no h2 e detalhada no h3).
    """
    chunks = []
    heading_re = re.compile(r'^#{1,4}\s+(.+)')
    lines = text.split('\n')
    cur_title, cur_lines, prev_tail = '', [], ''

    def flush():
        body = '\n'.join(cur_lines).strip()
        if len(body) < 40:
            return
        full = (f"[Contexto: {prev_tail}]\n\n" if prev_tail else '') + \
               (f"**{cur_title}**\n" if cur_title else '') + body
        chunks.append({
            'text': full,
            'section': cur_title,
            **meta,
            'filename': filename,
            'token_estimate': int(len(full.split()) * 1.33),
        })

    for line in lines:
        m = heading_re.match(line)
        if m:
            if cur_lines:
                flush()
                tail_lines = [l for l in cur_lines if l.strip()]
                prev_tail = ' '.join(tail_lines[-2:])[:180] if tail_lines else ''
            cur_title = m.group(1).strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    if cur_lines:
        flush()
    return chunks


# ─────────────────────────────────────────────
# 3. INGESTÃO
# ─────────────────────────────────────────────

def ingest_documents(docs_dir: str) -> Tuple[List[Dict], List[str], List[str]]:
    """Lê docs, chunka, retorna lista de chunks com textos e IDs."""
    all_chunks, texts, ids = [], [], []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith('.md'):
            continue
        meta = DOC_METADATA.get(fname, {'doc_id': fname, 'version': '?', 'date': '?', 'type': '?'})
        with open(os.path.join(docs_dir, fname), encoding='utf-8') as f:
            doc_text = f.read()
        chunks = chunk_document(doc_text, meta, fname)
        print(f"  [{meta['doc_id']}] → {len(chunks)} chunks")
        for i, c in enumerate(chunks):
            cid = f"{meta['doc_id']}__s{i}"
            all_chunks.append(c)
            texts.append(c['text'])
            ids.append(cid)
    return all_chunks, texts, ids


def build_chroma_collection(chunks, texts, ids, idf, vocab):
    """Constrói coleção ChromaDB com embeddings TF-IDF manuais."""
    client = chromadb.PersistentClient(path='./chroma_db')
    try:
        client.delete_collection('novatech')
    except Exception:
        pass
    coll = client.create_collection('novatech', metadata={'hnsw:space': 'cosine'})

    batch_size = 50
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        batch_texts  = texts[start:end]
        batch_ids    = ids[start:end]
        batch_chunks = chunks[start:end]
        batch_embs   = [tfidf_vector(t, idf, vocab) for t in batch_texts]
        batch_metas  = [{
            'doc_id':   c['doc_id'],
            'version':  c['version'],
            'date':     c['date'],
            'doc_type': c['type'],
            'section':  c['section'],
            'tokens':   str(c['token_estimate']),
        } for c in batch_chunks]
        coll.add(
            documents=batch_texts,
            embeddings=batch_embs,
            ids=batch_ids,
            metadatas=batch_metas,
        )
    return coll, client


# ─────────────────────────────────────────────
# 4. RETRIEVAL
# ─────────────────────────────────────────────

def retrieve(query: str, coll, idf: Dict[str, float], vocab: List[str], top_k: int = 5) -> List[Dict]:
    """
    Recupera top_k chunks mais relevantes.
    Boosts aplicados:
      +0.08 para docs normativos/contratuais sobre FAQ informal
      +0.05 para PROC-042-v2 (versão mais recente em conflito com v1)
    """
    q_emb = tfidf_vector(query, idf, vocab)
    results = coll.query(query_embeddings=[q_emb], n_results=top_k,
                         include=['documents', 'metadatas', 'distances'])

    chunks_out = []
    for doc, meta, dist in zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ):
        # ChromaDB retorna distância cosine (0=idêntico, 2=oposto)
        base_score = 1.0 - (dist / 2.0)
        boost = 0.0
        if meta.get('doc_type') in ('normativo', 'contratual'):
            boost += 0.08
        if meta.get('doc_id') == 'PROC-042-v2':
            boost += 0.05
        chunks_out.append({
            'score':    round(base_score + boost, 4),
            'text':     doc,
            'doc_id':   meta.get('doc_id', '?'),
            'version':  meta.get('version', '?'),
            'date':     meta.get('date', '?'),
            'doc_type': meta.get('doc_type', '?'),
            'section':  meta.get('section', '?'),
        })
    chunks_out.sort(key=lambda x: x['score'], reverse=True)
    return chunks_out


# ─────────────────────────────────────────────
# 5. MONTAGEM DE PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Você é o Assistente de Atendimento da NovaTech Logística.

## REGRAS — siga todas sem exceção
1. CITE FONTE: toda afirmação factual deve incluir "(Fonte: [DOC_ID] v[versão])".
2. NÃO INVENTE: se a informação não estiver nos trechos abaixo, responda exatamente:
   "Não encontrei essa informação na documentação disponível. Recomendo escalar para o supervisor."
3. DOCUMENTOS CONTRADITÓRIOS: se chunks de versões diferentes divergirem, apresente
   AMBOS e indique qual é mais recente. Nunca escolha silenciosamente.
4. TIER PLATINUM NÃO EXISTE: os tiers são Gold, Silver e Standard apenas.
5. CARGA PERIGOSA: NÃO pode ser devolvida pelo processo padrão (POL-001 §3.2).
   Oriente sempre o ramal 4500 (Gestão de Riscos).
6. FAQ é fonte INFORMAL. Se contradiz POL/PROC/SLA, prevalece o normativo.
7. Português formal e acessível. Sem jargão técnico desnecessário.
"""

def build_prompt(query: str, chunks: List[Dict],
                 client_tier: Optional[str] = None,
                 history: Optional[List[str]] = None) -> str:
    """
    Anatomia do contexto (orçamento GPT-4o 128K tokens):
      system_prompt estático  :  ~300 t  (fixo)
      metadados do cliente    :   ~50 t  (dinâmico)
      histórico (sliding 5)   : ~1.000 t (dinâmico, cresce com sessão)
      chunks (5 × ~500t)      : ~2.500 t (dinâmico)
      pergunta do atendente   :   ~50 t  (dinâmico)
      ─────────────────────────────────
      TOTAL estimado          : ~3.900 t  (<<<< limite 128K)

    Risco de context rot: sessões longas no Teams podem acumular histórico.
    Mitigação: sliding window máximo de 5 turnos.
    """
    parts = [SYSTEM_PROMPT]

    if client_tier:
        parts.append(f"\n## CONTEXTO\nTier do cliente: **{client_tier}**\n")

    if history:
        window = history[-5:]
        parts.append("\n## HISTÓRICO DA CONVERSA (últimos 5 turnos)\n" + "\n".join(window))

    parts.append("\n## DOCUMENTAÇÃO RECUPERADA — use APENAS estas informações\n")

    # Alerta de conflito
    doc_ids = [c['doc_id'] for c in chunks]
    for a, b in CONFLICTING_PAIRS:
        if a in doc_ids and b in doc_ids:
            parts.append(f"⚠️  CONFLITO DETECTADO: chunks de '{a}' e '{b}' presentes. "
                         f"Apresente AMBAS as versões ao atendente com as datas.\n")

    for i, c in enumerate(chunks, 1):
        conflict_note = ' ⚠️ EM CONFLITO COM OUTRA VERSÃO' if any(
            c['doc_id'] in pair for pair in CONFLICTING_PAIRS) else ''
        parts.append(
            f"--- Trecho {i} | {c['doc_id']} v{c['version']} ({c['date']}) "
            f"| {c['doc_type']}{conflict_note} | score={c['score']:.3f} ---\n"
            f"{c['text'][:700]}\n"
        )

    parts.append(f"\n## PERGUNTA DO ATENDENTE\n{query}\n\n## RESPOSTA\n")
    return '\n'.join(parts)


# ─────────────────────────────────────────────
# 6. TESTES — Mapa de cobertura do Anexo B
# ─────────────────────────────────────────────

TEST_CASES = [
    {
        "query": "Qual o prazo de devolução de mercadorias?",
        "expected_doc": "POL-001",
        "expected_behavior": "7 dias úteis + mencionar exceções para carga perigosa",
    },
    {
        "query": "Posso devolver carga perigosa?",
        "expected_doc": "POL-001",
        "expected_behavior": "NÃO pelo processo padrão → ramal 4500",
    },
    {
        "query": "Qual o SLA de incidentes críticos para cliente Gold?",
        "expected_doc": "SLA-2024",
        "expected_behavior": "Resposta 30min, resolução 4h",
    },
    {
        "query": "Qual o multiplicador regional para frete na região Norte?",
        "expected_doc": "PROC-042-v2",
        "expected_behavior": "1.8 (v2) — alertar sobre 1.6 na v1 desatualizada",
    },
    {
        "query": "Qual o SLA do cliente Platinum?",
        "expected_doc": "SLA-2024",
        "expected_behavior": "Tier Platinum NÃO EXISTE — listar Gold/Silver/Standard",
    },
]

def run_tests(coll, idf, vocab):
    print('\n' + '='*68)
    print('RESULTADOS DOS TESTES — PIPELINE RAG NOVATECH')
    print('='*68)
    passed = 0
    for i, tc in enumerate(TEST_CASES, 1):
        chunks = retrieve(tc['query'], coll, idf, vocab, top_k=5)
        prompt = build_prompt(tc['query'], chunks)
        top_ids = [c['doc_id'] for c in chunks[:3]]
        ok = tc['expected_doc'] in top_ids
        if ok:
            passed += 1
        print(f"\n{'─'*60}")
        print(f"TESTE {i}: {tc['query']}")
        print(f"  Esperado  : {tc['expected_doc']}")
        print(f"  Recuperado: {top_ids}")
        print(f"  Status    : {'✅ PASS' if ok else '❌ FAIL'}")
        print(f"  Comportamento esperado: {tc['expected_behavior']}")
        print(f"  Top chunks:")
        for c in chunks[:3]:
            flag = '✅' if c['doc_id'] == tc['expected_doc'] else '   '
            print(f"    {flag} [{c['doc_id']} v{c['version']}] score={c['score']:.4f} | sec: {c['section'][:45]}")
        # Mostra início do prompt para inspeção
        print(f"\n  --- Prompt (primeiros 400 chars) ---")
        print('  ' + prompt[:400].replace('\n', '\n  ') + '...')

    print(f"\n{'='*68}")
    print(f"SCORE FINAL: {passed}/{len(TEST_CASES)} testes passaram")

    print("""
PROBLEMAS IDENTIFICADOS (para correção em v2)
─────────────────────────────────────────────
1. SINONÍMIA GEOGRÁFICA [TF-IDF]:
   Pergunta "frete para Manaus" não recupera PROC-042-v2 porque o doc usa
   "região Norte", não "Manaus". TF-IDF não conhece a relação geográfica.
   → CORREÇÃO: embeddings semânticos (sentence-transformers) + gazetteer de
     mapeamento cidade→região como pré-processamento da query.

2. CHUNKING PARTE TABELAS AO MEIO:
   Seções longas com tabela no final podem ser cortadas se a tabela não tiver
   um heading próprio. Ex: tabela de multiplicadores na PROC-042-v1 fica no
   mesmo chunk que a introdução.
   → CORREÇÃO: detector de tabelas Markdown (regex `| … |`) como fronteira
     adicional de chunk, garantindo cada tabela como chunk atômico.

3. PRIORIDADE DE VERSÃO HARDCODED:
   O boost +0.05 para PROC-042-v2 está hardcoded. Se surgir PROC-042-v3,
   o código precisa ser atualizado manualmente.
   → CORREÇÃO: campo `superseded_by` nos metadados durante ingestão.
     Retrieval aplica penalidade automática a chunks com `superseded_by != null`.

4. CONTEXT ROT EM SESSÕES LONGAS:
   O sliding window de 5 turnos mitiga, mas em chamados longos (10+ perguntas)
   o atendente pode perder o contexto inicial (ex: o tier do cliente informado
   na pergunta 1 não aparece mais na pergunta 8).
   → CORREÇÃO: sumarização do histórico via LLM quando ultrapassa 5 turnos,
     preservando fatos-chave (tier, número do CT-e, tipo de carga).
""")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("Pipeline de RAG — NovaTech PoC\n")
    docs_dir = './docs'
    if not os.path.exists(docs_dir):
        print(f"ERRO: pasta {docs_dir} não encontrada.")
        return

    # Fase 1: Ingestão
    print("Fase 1: Ingestão e chunking")
    chunks, texts, ids = ingest_documents(docs_dir)
    print(f"Total: {len(chunks)} chunks\n")

    # Fase 2: Build TF-IDF corpus
    print("Fase 2: Construindo vocabulário TF-IDF")
    idf = build_vocab_and_idf(texts)
    vocab = sorted(idf.keys())
    print(f"Vocabulário: {len(vocab)} termos únicos\n")

    # Fase 3: Indexar no ChromaDB
    print("Fase 3: Indexando no ChromaDB")
    coll, _ = build_chroma_collection(chunks, texts, ids, idf, vocab)
    print(f"Indexação completa\n")

    # Fase 4: Testes
    run_tests(coll, idf, vocab)

    # Estatísticas de chunks por documento
    print("\nChunks por documento:")
    by_doc = Counter(c['doc_id'] for c in chunks)
    for doc_id, count in sorted(by_doc.items()):
        est_tokens = sum(c['token_estimate'] for c in chunks if c['doc_id'] == doc_id)
        print(f"  {doc_id}: {count} chunks | ~{est_tokens} tokens estimados")

    print("\n✅ Pipeline executado com sucesso.")
    print("Para obter respostas do LLM: copie o prompt de cada teste e cole no Claude.")

if __name__ == '__main__':
    main()
