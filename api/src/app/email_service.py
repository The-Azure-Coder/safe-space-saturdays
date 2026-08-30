import asyncio
import json
from collections.abc import Sequence
from urllib.request import Request, urlopen

from app.config import get_settings


async def send_transactional_email(*, recipient: str, subject: str, html: str, text: str, attachments: Sequence[dict[str, str]] | None = None, cc: Sequence[str] | None = None) -> bool:
    """Send through Brevo without exposing provider credentials to the client.

    Returning False keeps local development and approval workflows usable when
    email is not configured; the admin can retry after configuring Brevo.
    """
    settings = get_settings()
    if not settings.brevo_api_key or not settings.email_from_address:
        return False
    payload = {
        "sender": {"name": settings.email_from_name, "email": settings.email_from_address},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    if attachments:
        payload["attachment"] = list(attachments)
    if cc:
        payload["cc"] = [{"email": address} for address in cc]
    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": settings.brevo_api_key,
            "content-type": "application/json",
        },
        method="POST",
    )

    def deliver() -> bool:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed Brevo endpoint
            return 200 <= response.status < 300

    try:
        return await asyncio.to_thread(deliver)
    except Exception:
        return False
