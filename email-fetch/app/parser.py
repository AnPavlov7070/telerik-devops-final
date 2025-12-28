import hashlib
import re
from datetime import datetime, timezone
from email import message_from_bytes, policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import List, Optional, Tuple
from app.utils import extract_latest_reply_text

from bs4 import BeautifulSoup

from app.models import AttachmentMeta, EmailItem

DEAL_ID_RE = re.compile(r"\[Сделка:([A-Za-z0-9]{4,6})\]", re.UNICODE)


def _decode_str(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def _addresses(header_val: Optional[str]) -> List[str]:
    if not header_val:
        return []
    return [addr.strip() for _, addr in getaddresses([header_val]) if addr]


def _extract_best_text_and_html_flag(msg: Message) -> Tuple[Optional[str], bool]:
    """
    Prefer text/plain; if absent, fall back to HTML converted to text.
    Returns (plain_text, has_html).
    """
    plain_parts: List[str] = []
    html_parts: List[str] = []
    has_html = False

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()

            # Skip attachments and inline files
            if disp.startswith("attachment"):
                continue

            try:
                payload = part.get_payload(decode=True)
            except Exception:
                payload = None

            if not payload:
                continue

            if ctype == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    plain_parts.append(payload.decode(charset, errors="replace"))
                except Exception:
                    plain_parts.append(payload.decode("utf-8", errors="replace"))
            elif ctype == "text/html":
                has_html = True
                charset = part.get_content_charset() or "utf-8"
                try:
                    html_parts.append(payload.decode(charset, errors="replace"))
                except Exception:
                    html_parts.append(payload.decode("utf-8", errors="replace"))
    else:
        ctype = (msg.get_content_type() or "").lower()
        if ctype == "text/plain":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                plain_parts.append(payload.decode(charset, errors="replace"))
        elif ctype == "text/html":
            has_html = True
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                html_parts.append(payload.decode(charset, errors="replace"))

    text = None
    if plain_parts:
        text = "\n".join(plain_parts).strip()
    elif html_parts:
        # Convert HTML to text safely
        html_combined = "\n".join(html_parts)
        soup = BeautifulSoup(html_combined, "lxml")
        # remove script/style
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()

    return (text if text else None, has_html)


def _collect_attachments_meta(msg: Message) -> List[AttachmentMeta]:
    metas: List[AttachmentMeta] = []
    if not msg.is_multipart():
        return metas

    for part in msg.walk():
        disp = part.get("Content-Disposition") or ""
        if disp.lower().startswith("attachment"):
            filename = _decode_str(part.get_filename())
            ctype = part.get_content_type() or None
            size = None
            try:
                payload = part.get_payload(decode=True)
                if payload is not None:
                    size = len(payload)
            except Exception:
                size = None
            metas.append(AttachmentMeta(filename=filename, contentType=ctype, size=size))
    return metas


def _pick_deal_id(subject: Optional[str], body_text: Optional[str]) -> Optional[str]:
    haystacks = []
    if subject:
        haystacks.append(subject)
    if body_text:
        haystacks.append(body_text)
    for text in haystacks:
        m = DEAL_ID_RE.search(text)
        if m:
            return m.group(1)
    return None


def _message_id_or_hash(raw_bytes: bytes, msg: Message) -> str:
    mid = msg.get("Message-ID") or msg.get("Message-Id") or msg.get("Message-Id".lower())
    mid = _decode_str(mid) if mid else None
    if mid:
        return mid.strip()
    sha = hashlib.sha256(raw_bytes).hexdigest()
    return f"sha256:{sha}"


def _to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_email_bytes_to_item(raw_bytes: bytes, internaldate_utc: datetime) -> tuple[EmailItem, str]:
    """
    Parse a raw RFC822 message into EmailItem and return (item, identity_key).
    The identity_key is either Message-ID or sha256 hash of the raw bytes.
    """
    msg: EmailMessage = message_from_bytes(raw_bytes, policy=policy.default)

    identity = _message_id_or_hash(raw_bytes, msg)

    subject = _decode_str(msg.get("Subject"))
    from_raw = _decode_str(msg.get("From"))
    to_list = _addresses(msg.get("To"))
    cc_list = _addresses(msg.get("Cc"))

    # Original Date header (may differ from INTERNALDATE); normalize if parseable
    date_hdr = msg.get("Date")
    parsed_date = None
    if date_hdr:
        try:
            parsed_date = parsedate_to_datetime(date_hdr)
        except Exception:
            parsed_date = None

    body_text, has_html = _extract_best_text_and_html_flag(msg)
    snippet = (body_text[:200] if body_text else None)
    body_latest = extract_latest_reply_text(body_text or "") if body_text else None


    attachments_meta = _collect_attachments_meta(msg)

    deal_id = _pick_deal_id(subject, body_text)

    item = EmailItem(
        messageId=identity,
        subject=subject,
        **{"from": from_raw},
        to=to_list,
        cc=cc_list,
        date=_to_utc_iso(parsed_date) if parsed_date else None,
        receivedAt=_to_utc_iso(internaldate_utc),
        snippet=snippet,
        bodyText=body_text,
        bodyTextLatest=body_latest,
        hasHtml=has_html,
        attachmentsMeta=attachments_meta,
        dealId=deal_id,
    )
    return item, identity
