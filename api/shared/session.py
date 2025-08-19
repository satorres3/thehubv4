import base64
import hashlib
import json
from typing import Any, Dict

from cryptography.fernet import Fernet

from .config import SESSION_SECRET


def _get_key() -> bytes:
    # Derive a 32-byte key from SESSION_SECRET using SHA-256
    digest = hashlib.sha256(SESSION_SECRET.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_get_key())


def encrypt_session(data: Dict[str, Any]) -> str:
    serialized = json.dumps(data).encode()
    return _fernet.encrypt(serialized).decode()


def decrypt_session(token: str) -> Dict[str, Any]:
    decrypted = _fernet.decrypt(token.encode()).decode()
    return json.loads(decrypted)

