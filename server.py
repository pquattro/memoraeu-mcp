"""
MemoraEU MCP Server
Transport : stdio (Claude Desktop)

Chiffrement : AES-256-GCM zero-knowledge
- MEMORAEU_SECRET  : mot de passe dans .env
- MEMORAEU_SALT    : salt dans .env
- La clé est dérivée au démarrage, jamais transmise au serveur

Mémoire automatique :
- La ressource memoraeu://context est lue automatiquement en début de session
- recall est déclenché automatiquement sur le sujet du premier message
- remember est utilisé automatiquement sur les infos importantes
"""
import asyncio
import httpx
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Prompt, PromptMessage, GetPromptResult
from mcp.types import Resource, ResourceContents, TextResourceContents

API_URL = os.getenv("MEMORAEU_API_URL", "http://localhost:8000")
MEMORAEU_API_KEY = os.getenv("MEMORAEU_API_KEY", "")
MEMORAEU_SECRET = os.getenv("MEMORAEU_SECRET", "")
MEMORAEU_SALT = os.getenv("MEMORAEU_SALT", "memoraeu-default-salt-v1")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
COMPRESSION_THRESHOLD = 300
DEDUP_SKIP_THRESHOLD  = 0.94   # score ≥ 0.94 → doublon exact, on skip
DEDUP_WARN_THRESHOLD  = 0.85   # score ≥ 0.85 → très similaire, on avertit mais on stocke

_key: bytes | None = None
_context_loaded: bool = False
_session_context: str = ""
_first_recall: bool = True

def get_key() -> bytes | None:
    return _key

def init_crypto():
    global _key
    if MEMORAEU_SECRET:
        from crypto import derive_key
        _key = derive_key(MEMORAEU_SECRET, MEMORAEU_SALT)
        print("[memoraeu] ✅ Chiffrement zero-knowledge activé", file=sys.stderr)
    else:
        print("[memoraeu] ⚠️  MEMORAEU_SECRET absent — stockage en clair", file=sys.stderr)

def encrypt_content(content: str) -> str:
    key = get_key()
    if not key:
        return content
    from crypto import encrypt
    return encrypt(content, key)

def decrypt_content(value: str) -> str:
    key = get_key()
    if not key:
        return value
    from crypto import decrypt, is_encrypted
    if not is_encrypted(value):
        return value
    try:
        return decrypt(value, key)
    except Exception:
        return "[contenu chiffré — clé incorrecte]"

async def _mistral_chat(prompt: str) -> str | None:
    """Appel direct à Mistral pour compression ou catégorisation (avant chiffrement)."""
    if not MISTRAL_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{MISTRAL_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
                json={"model": MISTRAL_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 400, "temperature": 0.1}
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[mcp] Mistral error: {e}", file=sys.stderr)
        return None

async def embed_locally(content: str) -> list[float] | None:
    """Génère l'embedding depuis le texte clair (avant chiffrement) — zero-knowledge."""
    if not MISTRAL_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{MISTRAL_BASE_URL}/embeddings",
                headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
                json={"model": "mistral-embed", "inputs": [content]}
            )
            r.raise_for_status()
            return r.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"[mcp] Embedding error: {e}", file=sys.stderr)
        return None

async def compress_locally(content: str) -> str:
    """Compresse le contenu en clair avant chiffrement."""
    if len(content) <= COMPRESSION_THRESHOLD:
        return content
    prompt = (
        "Résume ce texte en 1-3 phrases concises, en français, en gardant l'essentiel. "
        "Réponds uniquement avec le résumé, sans introduction ni conclusion.\n\n"
        f"{content}"
    )
    compressed = await _mistral_chat(prompt)
    if compressed and len(compressed) < len(content):
        print(f"[mcp] Compression: {len(content)} → {len(compressed)} chars", file=sys.stderr)
        return compressed
    return content

async def suggest_category_locally(content: str, existing: list[str]) -> str:
    """Suggère une catégorie pour le contenu en clair."""
    existing_str = ", ".join(existing) if existing else "aucune"
    prompt = (
        f"Catégories existantes : {existing_str}\n\n"
        f"Texte : {content[:500]}\n\n"
        "Quelle catégorie courte (1-2 mots, en français, minuscules) correspond le mieux ? "
        "Utilise une existante si pertinente, sinon crée-en une. Réponds uniquement avec la catégorie."
    )
    cat = await _mistral_chat(prompt)
    if cat:
        return cat.lower().strip().strip('"').strip("'")[:30]
    return "personnel"

async def check_duplicate(embedding: list[float]) -> dict | None:
    """
    Recherche une mémoire similaire via le vecteur pré-calculé (zero-knowledge).
    Retourne {"id", "score", "preview"} si un doublon est trouvé, sinon None.
    """
    if not embedding:
        return None
    try:
        response = await api_post("/memories/search-by-vector", {
            "vector": embedding,
            "limit": 1,
            "scope": "private",
            "threshold": DEDUP_WARN_THRESHOLD,
        })
        results = response.get("results", [])
        if not results:
            return None
        best = results[0]
        m = best["memory"]
        return {
            "id": m["id"],
            "score": best["score"],
            "preview": decrypt_content(m["content"])[:120],
        }
    except Exception as e:
        print(f"[mcp] Dedup check error: {e}", file=sys.stderr)
        return None


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {MEMORAEU_API_KEY}"} if MEMORAEU_API_KEY else {}

async def api_post(path: str, body: dict, timeout: float = 90.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{API_URL}{path}", json=body, headers=_auth_headers())
        r.raise_for_status()
        return r.json()

async def api_get(path: str, params: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{API_URL}{path}", params=params, headers=_auth_headers())
        r.raise_for_status()
        return r.json()

async def api_delete(path: str) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(f"{API_URL}{path}", headers=_auth_headers())
        return r.status_code == 204

async def load_session_context() -> str:
    """
    Charge les mémoires récentes au premier appel de la session.
    Injecté automatiquement dans recall pour enrichir le contexte.
    """
    global _context_loaded, _session_context
    if _context_loaded:
        return _session_context
    try:
        memories = await api_get("/memories", params={"limit": 10, "scope": "private"})
        if memories:
            lines = ["[Contexte mémoire automatique — MemoraEU]"]
            for m in memories:
                content = decrypt_content(m["content"])
                cat = m.get("category") or "—"
                lines.append(f"[{cat}] {content[:120]}")
            _session_context = "\n".join(lines)
        else:
            _session_context = ""
    except Exception:
        _session_context = ""
    _context_loaded = True
    return _session_context

app = Server("memoraeu")

SYSTEM_PROMPT_TEXT = """Tu as accès à une mémoire persistante via les outils MemoraEU.

## Mémorisation automatique
Sans que l'utilisateur ait besoin de te le demander, utilise `remember` dès qu'une information mérite d'être retenue :
- Préférences personnelles ("j'aime", "je préfère", "je veux toujours")
- Décisions importantes ("on a décidé", "le choix final est")
- Faits biographiques (lieu, famille, travail, projets)
- Habitudes récurrentes ou contraintes durables
- Informations techniques propres à l'utilisateur (stack, config, credentials non-sensibles)

## Rappel automatique
Dès le premier message de l'utilisateur, utilise `recall` avec le sujet détecté comme query.
N'attends pas qu'on te le demande — c'est automatique.

## Règles
- Ne mémorise pas les informations générales ou éphémères (météo du jour, blagues, calculs ponctuels)
- Si l'utilisateur dit "oublie ça" ou "ne retiens pas", utilise `forget`
- Confirme discrètement les mémorisations : une ligne, pas plus
- Optimisation tokens : limite recall à 3 résultats par défaut, mémoires compactes
"""

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="memoraeu_system",
            description="Système de mémorisation automatique MemoraEU — injecter en system prompt.",
            arguments=[]
        )
    ]

@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    if name == "memoraeu_system":
        return GetPromptResult(
            description="Comportement de mémorisation automatique",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=SYSTEM_PROMPT_TEXT)
                )
            ]
        )
    raise ValueError(f"Prompt inconnu : {name}")

@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="memoraeu://context",
            name="Contexte mémoire MemoraEU",
            description="Mémoires récentes injectées automatiquement en début de session",
            mimeType="text/plain"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> list[ResourceContents]:
    if uri == "memoraeu://context":
        context = await load_session_context()
        text = context if context else "Aucune mémoire enregistrée."
        return [TextResourceContents(uri=uri, mimeType="text/plain", text=text)]
    raise ValueError(f"Ressource inconnue : {uri}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="remember",
            description=(
                "Mémorise automatiquement une information importante. "
                "UTILISE CET OUTIL SANS QU'ON TE LE DEMANDE dès que l'utilisateur exprime "
                "une préférence, une décision, un fait biographique, une config technique, "
                "ou une contrainte durable. Confirme en une ligne discrète."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="recall",
            description=(
                "APPELLE CET OUTIL AUTOMATIQUEMENT dès le premier message de chaque conversation. "
                "Utilise le sujet du message comme query pour récupérer le contexte pertinent. "
                "Recherche sémantique — pas besoin de mots exacts. "
                "Limite à 3 résultats pour économiser les tokens (augmente seulement si nécessaire)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 3},
                    "category": {"type": "string"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="forget",
            description="Supprime une mémoire par son ID.",
            inputSchema={
                "type": "object",
                "properties": {"memory_id": {"type": "string"}},
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="list_memories",
            description="Liste les mémoires récentes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="list_categories",
            description="Retourne les catégories existantes triées par usage.",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "remember":
        try:
            raw_content = arguments["content"]

            # 1. Compression en clair (avant chiffrement)
            content = await compress_locally(raw_content)

            # 2. Catégorisation en clair (avant chiffrement)
            category = arguments.get("category")
            if not category:
                try:
                    cats_resp = await api_get("/memories/categories")
                    existing = [c["name"] for c in cats_resp.get("categories", [])]
                except Exception:
                    existing = []
                category = await suggest_category_locally(content, existing)

            # 3. Embedding depuis le texte clair (zero-knowledge)
            embedding = await embed_locally(content)

            # 3b. Déduplication — recherche par vecteur avant chiffrement
            if embedding:
                dup = await check_duplicate(embedding)
                if dup:
                    score_pct = round(dup["score"] * 100)
                    if dup["score"] >= DEDUP_SKIP_THRESHOLD:
                        return [TextContent(type="text", text=(
                            f"⚠️ Doublon détecté ({score_pct}% similaire) — mémoire non créée.\n"
                            f"→ Existante : {dup['preview']} (ID: {dup['id'][:8]}…)"
                        ))]
                    else:
                        print(f"[mcp] Mémoire similaire à {score_pct}% (ID: {dup['id'][:8]}…) — stockage quand même", file=sys.stderr)

            # 4. Chiffrement du contenu traité
            encrypted = encrypt_content(content)

            # 5. Envoi à l'API avec pre_processed=True + embedding pré-calculé
            payload = {
                "content": encrypted,
                "category": category,
                "tags": arguments.get("tags", []),
                "source": "claude_desktop",
                "scope": "private",
                "pre_processed": True,
            }
            if embedding:
                payload["embedding"] = embedding
            memory = await api_post("/memories", payload)
            cat = memory.get("category") or "non catégorisé"
            lock = "🔒" if get_key() else "📝"
            return [TextContent(type="text", text=f"✅ Mémorisé {lock} (ID: {memory['id'][:8]}…, catégorie: {cat})")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erreur : {e}")]

    elif name == "recall":
        global _first_recall
        try:
            is_first = _first_recall
            _first_recall = False

            # Chargement du contexte session au premier recall
            context = await load_session_context()

            response = await api_post("/memories/search", {
                "query": arguments["query"],
                "limit": arguments.get("limit", 3),
                "category": arguments.get("category"),
                "scope": "private"
            })
            results = response.get("results", [])

            lines = []

            # Injection du system prompt uniquement au premier recall
            if is_first:
                lines.append(SYSTEM_PROMPT_TEXT)
                lines.append("---")

            if context and not results:
                lines.append(context)
            elif not results:
                if not is_first:
                    return [TextContent(type="text", text="Aucune mémoire trouvée.")]
            else:
                lines.append(f"🔍 {len(results)} mémoire(s) :\n")
                for r in results:
                    m = r["memory"]
                    content = decrypt_content(m["content"])
                    cat = m.get("category") or "—"
                    tags = ", ".join(m.get("tags", [])) or "—"
                    lines.append(
                        f"• [{round(r['score']*100)}%] {content}\n"
                        f"  catégorie: {cat} | tags: {tags} | ID: {m['id'][:8]}…"
                    )
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erreur : {e}")]

    elif name == "forget":
        try:
            deleted = await api_delete(f"/memories/{arguments['memory_id']}")
            return [TextContent(type="text", text="🗑️ Supprimée." if deleted else "Introuvable.")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erreur : {e}")]

    elif name == "list_memories":
        try:
            params = {"limit": arguments.get("limit", 20), "scope": "private"}
            if arguments.get("category"):
                params["category"] = arguments["category"]
            memories = await api_get("/memories", params=params)
            if not memories:
                return [TextContent(type="text", text="Aucune mémoire.")]
            lines = [f"📋 {len(memories)} mémoire(s) :\n"]
            for m in memories:
                content = decrypt_content(m["content"])
                preview = content[:100] + ("…" if len(content) > 100 else "")
                lines.append(f"• [{m.get('category') or '—'}] {preview} (ID: {m['id'][:8]}…)")
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erreur : {e}")]

    elif name == "list_categories":
        try:
            response = await api_get("/memories/categories")
            cats = response.get("categories", [])
            if not cats:
                return [TextContent(type="text", text="Aucune catégorie.")]
            lines = ["📁 Catégories :\n"] + [f"• {c['name']} ({c['usage_count']})" for c in cats]
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erreur : {e}")]

    return [TextContent(type="text", text=f"Outil inconnu : {name}")]

async def main():
    init_crypto()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())