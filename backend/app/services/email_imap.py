import email
import imaplib
import logging
import uuid
from datetime import datetime

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def is_imap_configured() -> bool:
    """Retourne True si IMAP est configuré (host, user, password non vides)."""
    return bool(
        settings.imap_host and settings.imap_user and settings.imap_password
    )


def _connect():
    if settings.imap_ssl:
        client = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    else:
        client = imaplib.IMAP4(settings.imap_host, settings.imap_port)
    client.login(settings.imap_user, settings.imap_password)
    client.select(settings.imap_folder)
    return client


def fetch_unseen_messages() -> list[dict]:
    if not is_imap_configured():
        return []
    try:
        client = _connect()
    except imaplib.IMAP4.error as e:
        logger.warning("IMAP authentication failed (check IMAP_HOST, IMAP_USER, IMAP_PASSWORD): %s", e)
        return []
    except Exception as e:
        logger.warning("IMAP connection error: %s", e)
        return []
    try:
        status, data = client.search(None, "UNSEEN")
        if status != "OK":
            return []
        ids = data[0].split()
        messages = []
        for msg_id in ids:
            status, msg_data = client.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            client.store(msg_id, "+FLAGS", "\\Seen")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            message_id = msg.get("Message-ID") or str(uuid.uuid4())
            subject = msg.get("Subject", "")
            from_addr = msg.get("From", "")
            date_raw = msg.get("Date")
            try:
                received_at = email.utils.parsedate_to_datetime(date_raw)
            except Exception:
                received_at = datetime.utcnow()
            snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        snippet = part.get_payload(decode=True)[:500].decode(
                            errors="ignore"
                        )
                        break
            else:
                payload = msg.get_payload(decode=True) or b""
                snippet = payload[:500].decode(errors="ignore")
            messages.append(
                {
                    "provider_message_id": message_id,
                    "from_addr": from_addr,
                    "subject": subject,
                    "snippet": snippet,
                    "received_at": received_at,
                    "raw_payload": {"headers": dict(msg.items())},
                    "idempotency_key": f"imap:{message_id}",
                }
            )
        return messages
    finally:
        try:
            client.close()
            client.logout()
        except Exception:
            pass
