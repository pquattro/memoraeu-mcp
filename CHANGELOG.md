# Changelog

All notable changes to `memoraeu-mcp` are documented here.  
*Toutes les modifications notables sont documentées ici.*

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) — [Semantic Versioning](https://semver.org/)

---

## [0.1.9] - 2026-05-12

### Added / Ajouté
- **`remember_fact`** — mémorise un fait structuré avec validité temporelle (subject, predicate, object) ; invalide automatiquement l'ancienne valeur sur le même prédicat. Chiffrement côté MCP avant envoi.
- **`recall_facts`** — rappel des faits actifs pour un sujet donné (valeur courante uniquement)
- **`invalidate_fact`** — invalide explicitement un fait par son ID
- **`api_put`** — helper interne pour les requêtes PUT vers l'API
- Manifestes marketplace mis à jour (`server.json`, `.claude-plugin/`)

### Changed / Modifié
- PBKDF2 : 210 000 itérations (recommandation OWASP 2024), préfixe `ENCv1:` sur les ciphertexts
- README : quick start, badges, section Why, Contributing, licence AGPL v3

---

## [0.1.5] - 2026-04-28

### Changed / Modifié
- PBKDF2 : 210k itérations + préfixe `ENCv1:` sur les ciphertexts
- Refonte sécurité complète (revue externe)

---

## [0.1.1] - 2026-04-19

### Fixed / Corrigé
- Package structure: `server.py` and `crypto.py` now fully embedded in `memoraeu_mcp/` — no external path dependency when installed via `pip` or `uvx`
- Structure du package : `server.py` et `crypto.py` intégrés dans `memoraeu_mcp/` — aucune dépendance de chemin externe lors de l'installation via `pip` ou `uvx`

---

## [0.1.0] - 2026-04-19

### Added / Ajouté
- Initial release / Version initiale
- Zero-knowledge AES-256-GCM encryption (PBKDF2-HMAC-SHA256, 100k iterations)
- Chiffrement zero-knowledge AES-256-GCM (PBKDF2-HMAC-SHA256, 100k itérations)
- MCP tools: `remember`, `recall`, `forget`, `list_memories`, `list_categories`
- Outils MCP : `remember`, `recall`, `forget`, `list_memories`, `list_categories`
- Pre-computed embeddings from plaintext before encryption (Mistral Embed)
- Embeddings calculés depuis le texte clair avant chiffrement (Mistral Embed)
- Client-side compression and categorization via Mistral
- Compression et catégorisation côté client via Mistral
- Near-duplicate detection before storing (vector similarity threshold 0.94)
- Détection de doublons avant stockage (similarité vectorielle seuil 0.94)
- Auto-inject system prompt on first `recall`
- Injection automatique du system prompt au premier `recall`
- Support for `meu-sk-xxx` API keys
- Support des clés API `meu-sk-xxx`
