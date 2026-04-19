"""
MemoraEU — Chiffrement zero-knowledge côté client
AES-256-GCM + PBKDF2-HMAC-SHA256

Le serveur ne voit jamais le texte clair ni la clé.
L'embedding est calculé AVANT chiffrement pour préserver la recherche sémantique.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# Salt fixe par installation (stocké dans .env)
# En phase 2 : un salt par user stocké côté serveur
PBKDF2_ITERATIONS = 100_000


def derive_key(password: str, salt: str) -> bytes:
    """
    Dérive une clé AES-256 depuis un mot de passe et un salt.
    Appelé une seule fois au démarrage du MCP server.
    """
    salt_bytes = salt.encode() if isinstance(salt, str) else salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode())


def encrypt(plaintext: str, key: bytes) -> str:
    """
    Chiffre un texte avec AES-256-GCM.
    Retourne : base64(nonce[12] + ciphertext + tag[16])
    """
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(ciphertext_b64: str, key: bytes) -> str:
    """
    Déchiffre un texte chiffré par encrypt().
    Lève une exception si la clé est mauvaise ou les données corrompues.
    """
    data = base64.b64decode(ciphertext_b64)
    nonce = data[:12]
    ciphertext = data[12:]
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def is_encrypted(value: str) -> bool:
    """
    Détecte si une valeur est déjà chiffrée (base64 valide de longueur minimale).
    Permet la compatibilité avec les mémoires existantes en clair.
    """
    try:
        data = base64.b64decode(value)
        return len(data) > 12  # nonce(12) + au moins 1 octet
    except Exception:
        return False
