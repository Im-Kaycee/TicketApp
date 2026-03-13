import hmac
import hashlib
from django.conf import settings


def generate_qr_signature(ticket_id: str) -> str:
    """
    HMAC-SHA256 signature over the ticket UUID.
    Stored on the ticket at creation; re-computed at scan time to verify.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        str(ticket_id).encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_qr_signature(ticket_id: str, provided: str) -> bool:
    """
    Constant-time comparison to prevent timing attacks.
    """
    expected = generate_qr_signature(ticket_id)
    return hmac.compare_digest(expected, provided)