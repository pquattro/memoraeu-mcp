# memoraeu-mcp

> 🇬🇧 [English](#english) | 🇫🇷 [Français](#français)

---

## English

**Zero-knowledge persistent memory layer for Claude — MCP server**

MemoraEU gives Claude a persistent, encrypted memory. All content is encrypted client-side with AES-256-GCM before reaching the server — the server never sees your plaintext. Semantic search is powered by Mistral embeddings + Qdrant.

### Features

- 🔒 **Zero-knowledge** — AES-256-GCM encryption, key never leaves your machine
- 🧠 **Semantic search** — Mistral embeddings + Qdrant vector store
- 🔄 **Auto memory** — remembers and recalls context automatically
- 🚫 **Deduplication** — detects near-duplicate memories before storing
- 🇪🇺 **EU hosted** — GDPR compliant infrastructure

### Installation

```bash
pip install memoraeu-mcp
```

Or with `uvx` (no install required):

```bash
uvx memoraeu-mcp
```

### Claude Desktop configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memoraeu": {
      "command": "uvx",
      "args": ["memoraeu-mcp"],
      "env": {
        "MEMORAEU_API_URL": "https://api.memoraeu.isquarecube.fr",
        "MEMORAEU_API_KEY": "meu-sk-...",
        "MEMORAEU_SECRET": "your-secret",
        "MEMORAEU_SALT": "your-salt",
        "MISTRAL_API_KEY": "your-mistral-key"
      }
    }
  }
}
```

### Getting your keys

1. Sign up at [app.memoraeu.isquarecube.fr](https://app.memoraeu.isquarecube.fr)
2. Go to **Settings** → copy `MEMORAEU_SECRET` and `MEMORAEU_SALT`
3. Create an API key → copy `MEMORAEU_API_KEY`
4. Get a Mistral API key at [console.mistral.ai](https://console.mistral.ai)

### Available tools

| Tool | Description |
|------|-------------|
| `remember` | Memorizes important information automatically |
| `recall` | Semantic search across stored memories |
| `forget` | Deletes a memory by ID |
| `list_memories` | Lists recent memories with optional category filter |
| `list_categories` | Returns existing categories sorted by usage |

### Self-hosting

The API is open source. Deploy your own instance with Docker:

```bash
git clone https://github.com/pquattro/memoraEu
cd memoraEu
docker compose up -d
```

---

## Français

**Couche mémoire persistante zero-knowledge pour Claude — serveur MCP**

MemoraEU donne à Claude une mémoire persistante et chiffrée. Tout le contenu est chiffré côté client en AES-256-GCM avant d'atteindre le serveur — le serveur ne voit jamais le texte en clair. La recherche sémantique est assurée par Mistral Embed + Qdrant.

### Fonctionnalités

- 🔒 **Zero-knowledge** — chiffrement AES-256-GCM, la clé ne quitte jamais votre machine
- 🧠 **Recherche sémantique** — embeddings Mistral + base vectorielle Qdrant
- 🔄 **Mémoire automatique** — mémorise et rappelle le contexte sans intervention
- 🚫 **Déduplication** — détecte les doublons avant stockage
- 🇪🇺 **Hébergé en Europe** — infrastructure conforme RGPD

### Installation

```bash
pip install memoraeu-mcp
```

Ou avec `uvx` (sans installation) :

```bash
uvx memoraeu-mcp
```

### Configuration Claude Desktop

Ajoutez dans votre `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "memoraeu": {
      "command": "uvx",
      "args": ["memoraeu-mcp"],
      "env": {
        "MEMORAEU_API_URL": "https://api.memoraeu.isquarecube.fr",
        "MEMORAEU_API_KEY": "meu-sk-...",
        "MEMORAEU_SECRET": "votre-secret",
        "MEMORAEU_SALT": "votre-salt",
        "MISTRAL_API_KEY": "votre-clé-mistral"
      }
    }
  }
}
```

### Obtenir vos clés

1. Créez un compte sur [app.memoraeu.isquarecube.fr](https://app.memoraeu.isquarecube.fr)
2. Allez dans **Paramètres** → copiez `MEMORAEU_SECRET` et `MEMORAEU_SALT`
3. Créez une clé API → copiez `MEMORAEU_API_KEY`
4. Obtenez une clé Mistral sur [console.mistral.ai](https://console.mistral.ai)

### Outils disponibles

| Outil | Description |
|-------|-------------|
| `remember` | Mémorise automatiquement les informations importantes |
| `recall` | Recherche sémantique dans les mémoires stockées |
| `forget` | Supprime une mémoire par son ID |
| `list_memories` | Liste les mémoires récentes avec filtre optionnel |
| `list_categories` | Retourne les catégories existantes triées par usage |

### Auto-hébergement

L'API est open source. Déployez votre propre instance avec Docker :

```bash
git clone https://github.com/pquattro/memoraEu
cd memoraEu
docker compose up -d
```

---

## License

MIT © 2026 MemoraEU
