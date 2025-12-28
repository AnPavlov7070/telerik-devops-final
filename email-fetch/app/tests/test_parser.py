from datetime import datetime, timezone
from email.message import EmailMessage

from app.parser import parse_email_bytes_to_item


def _make_email(subject: str, body: str) -> bytes:
    msg = EmailMessage()
    msg["From"] = "Sender <sender@example.com>"
    msg["To"] = "to@example.com"
    msg["Subject"] = subject
    msg["Message-ID"] = "<abc@example.com>"
    msg["Date"] = "Sun, 28 Sep 2025 12:34:56 +0000"
    msg.set_content(body)
    return msg.as_bytes()


def test_deal_id_extraction_subject():
    raw = _make_email("Здравейте [Сделка:AB12C3]", "Body")
    internal = datetime(2025, 9, 28, 12, 34, 56, tzinfo=timezone.utc)
    item, ident = parse_email_bytes_to_item(raw, internal)
    assert item.dealId == "AB12C3"
    assert item.messageId == "<abc@example.com>"


def test_deal_id_extraction_body():
    raw = _make_email("No deal", "Текст с маркер [Сделка:ZZ9911] тук.")
    internal = datetime(2025, 9, 28, 12, 34, 56, tzinfo=timezone.utc)
    item, _ = parse_email_bytes_to_item(raw, internal)
    assert item.dealId == "ZZ9911"


def test_body_latest_cuts_history_and_removes_quote_lines():
    body = (
        "Latest line 1\r\n"
        "Latest line 2\r\n"
        "\r\n"
        "> quoted should be removed\r\n"
        "On Wed, Oct 22, 2025 at 8:19 PM Someone <x@y> wrote:\r\n"
        "Older thread line\r\n"
        "> older quoted\r\n"
    )
    raw = _make_email("Subject", body)
    internal = datetime(2025, 9, 28, 12, 34, 56, tzinfo=timezone.utc)

    item, _ = parse_email_bytes_to_item(raw, internal)

    assert item.bodyText is not None
    assert "Older thread line" in item.bodyText  # raw body unchanged

    assert item.bodyTextLatest == "Latest line 1\nLatest line 2"
    
def test_body_latest_cuts_gmail_marker_split_wrote_line():
    body = (
        "New latest text\r\n\r\n"
        "On Sun, Dec 28, 2025 at 2:04 PM David Pavlov <davidpavlov80@gmail.com>\r\n"
        "wrote:\r\n\r\n"
        "> Test 9\r\n"
    )
    raw = _make_email("Subject", body)
    internal = datetime(2025, 12, 28, 12, 34, 56, tzinfo=timezone.utc)

    item, _ = parse_email_bytes_to_item(raw, internal)
    assert item.bodyTextLatest == "New latest text"


def test_body_latest_cuts_bulgarian_original_message_marker_even_if_quoted():
    body = (
        "АБВ ТЕСТ 3\r\n\r\n"
        " >-------- Оригинално писмо --------\r\n"
        " >От: David Pavlov <davidpavlov80@gmail.com>\r\n"
        " >Относно: Re: [Сделка:SCV80] 2ри тест мейл\r\n"
    )
    raw = _make_email("Subject", body)
    internal = datetime(2025, 12, 28, 12, 34, 56, tzinfo=timezone.utc)

    item, _ = parse_email_bytes_to_item(raw, internal)
    assert item.bodyTextLatest == "АБВ ТЕСТ 3"
