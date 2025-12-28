import pytest
from app.utils import extract_latest_reply_text


@pytest.mark.parametrize(
    "name,body,expected",
    [
        # 1) Gmail classic (same line wrote:)
        (
            "gmail_same_line",
            "Latest reply\n\nOn Wed, Oct 22, 2025 at 8:19 PM Someone <x@y> wrote:\n> older\n",
            "Latest reply",
        ),
        # 2) Gmail split wrote line (your real case)
        (
            "gmail_split_wrote",
            "New latest text\r\n\r\nOn Sun, Dec 28, 2025 at 2:04 PM David <a@b>\r\nwrote:\r\n\r\n> Test 9\r\n",
            "New latest text",
        ),
        # 3) Gmail marker with quoted prefix (> On ... wrote:)
        (
            "gmail_quoted_marker",
            "Latest\n\n> On Wed, Oct 22, 2025 at 8:19 PM Someone <x@y> wrote:\n> older\n",
            "Latest",
        ),
        # 4) Outlook original message (exact)
        (
            "outlook_original_message",
            "Latest line\n\n-----Original Message-----\nFrom: A <a@a>\n",
            "Latest line",
        ),
        # 5) Outlook original message with variable dashes/spaces
        (
            "outlook_original_message_var",
            "Top\n\n-------- Original Message --------\nFrom: A <a@a>\n",
            "Top",
        ),
        # 6) Forwarded message separator (common)
        (
            "forwarded_message_dashes",
            "Hi\n\n----- Forwarded message -----\nFrom: A <a@a>\n",
            "Hi",
        ),
        # 7) Begin forwarded message (Apple Mail / others)
        (
            "begin_forwarded_message",
            "Hello\n\nBegin forwarded message\nFrom: A <a@a>\n",
            "Hello",
        ),
        # 8) Begin forwarded message with colon
        (
            "begin_forwarded_message_colon",
            "Hello\n\nBegin forwarded message:\nFrom: A <a@a>\n",
            "Hello",
        ),
        # 9) Header block marker From: (English)
        (
            "header_from_en",
            "Latest\n\nFrom: Someone <x@y>\nSent: ...\n",
            "Latest",
        ),
        # 10) Header block marker Sent: (English)
        (
            "header_sent_en",
            "Latest\n\nSent: Sunday, December 28, 2025 2:18 PM\nTo: ...\n",
            "Latest",
        ),
        # 11) Bulgarian original message marker (ABV)
        (
            "bg_original_message",
            "АБВ ТЕСТ 3\n\n-------- Оригинално писмо --------\nОт: David <x@y>\n",
            "АБВ ТЕСТ 3",
        ),
        # 12) Bulgarian original message marker with quote prefix
        (
            "bg_original_message_quoted",
            "АБВ ТЕСТ 3\r\n\r\n >-------- Оригинално писмо --------\r\n >От: David <x@y>\r\n",
            "АБВ ТЕСТ 3",
        ),
        # 13) Bulgarian header block marker От:
        (
            "bg_header_ot",
            "Тест\n\nОт: Иван <x@y>\nДо: ...\n",
            "Тест",
        ),
        # 14) Bulgarian header marker Изпратено на:
        (
            "bg_header_sent",
            "Тест\n\nИзпратено на: 28.12.2025 14:19\nДо: ...\n",
            "Тест",
        ),
        # 15) German reply marker: "Am ... schrieb:"
        (
            "de_am_schrieb",
            "Antwort\n\nAm 28.12.2025 um 14:19 schrieb David <x@y>:\n> Alt\n",
            "Antwort",
        ),
        # 16) French reply marker: "Le ... a écrit :"
        (
            "fr_le_a_ecrit",
            "Réponse\n\nLe 28 déc. 2025 à 14:19, David <x@y> a écrit :\n> Ancien\n",
            "Réponse",
        ),
        # 17) Spanish reply marker: "El ... escribió:"
        (
            "es_el_escribio",
            "Respuesta\n\nEl 28 dic 2025, 14:19, David <x@y> escribió:\n> Antiguo\n",
            "Respuesta",
        ),
        # 18) Italian reply marker: "Il ... ha scritto:"
        (
            "it_il_ha_scritto",
            "Risposta\n\nIl giorno 28 dic 2025 alle ore 14:19 David <x@y> ha scritto:\n> Vecchio\n",
            "Risposta",
        ),
        # 19) Portuguese reply marker: "Em ... escreveu:"
        (
            "pt_em_escreveu",
            "Resposta\n\nEm 28/12/2025 14:19, David <x@y> escreveu:\n> Antigo\n",
            "Resposta",
        ),
        # 20) Dutch reply marker: "Op ... schreef:"
        (
            "nl_op_schreef",
            "Antwoord\n\nOp 28 dec 2025 om 14:19 schreef David <x@y>:\n> Oud\n",
            "Antwoord",
        ),
    ],
)
def test_extract_latest_reply_text_top20(name: str, body: str, expected: str):
    assert extract_latest_reply_text(body) == expected


def test_removes_quote_prefixed_lines_before_trim():
    body = "Line1\n\n> quoted1\n> quoted2\n\nLine2\n"
    # No history markers; only remove quote lines
    assert extract_latest_reply_text(body) == "Line1\n\nLine2"


def test_fallback_when_everything_is_quoted_in_top_part():
    body = (
        "> quoted only line\n"
        "> second quoted\n"
        "On Wed, Oct 22, 2025 at 8:19 PM Someone <x@y> wrote:\n"
        "> older\n"
    )
    # Cut at On... wrote, top-part becomes only quoted lines -> cleaned empty
    # Fallback returns trimmed top-part (still only quoted lines, but per spec fallback is pre '>' removal)
    assert extract_latest_reply_text(body) == "> quoted only line\n> second quoted"