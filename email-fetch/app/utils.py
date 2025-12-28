import re
from datetime import date, datetime, timezone
from typing import Iterable, Optional


def to_imap_date(dt: datetime) -> date:
    """
    Convert a timezone-aware datetime to IMAP date (YYYY-Mon-DD as date object).
    IMAPClient accepts date objects directly.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def max_iso(values: Iterable[Optional[str]]) -> Optional[str]:
    mx = None
    mx_dt = None
    for v in values:
        if not v:
            continue
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if mx_dt is None or dt > mx_dt:
            mx_dt = dt
            mx = v
    return mx


# We treat these as "quoted history markers" and cut at their earliest occurrence.
# Implementation notes:
# - All patterns are line-anchored: ^ ... $
# - We allow optional quote prefix (> and whitespace) before the marker.
# - Patterns are case-insensitive and multiline.
# - This list intentionally includes localized variants commonly seen in replies/forwards.
_MARKER_LINE_PATTERNS = [
    # Outlook / Exchange "Original Message" (English)
    re.compile(r"(?im)^\s*>?\s*-+\s*Original Message\s*-+\s*$"),
    # Gmail / Yahoo / generic forwarded separator
    re.compile(r"(?im)^\s*>?\s*-+\s*Forwarded message\s*-+\s*$"),
    re.compile(r"(?im)^\s*>?\s*Begin forwarded message\s*$"),
    re.compile(r"(?im)^\s*>?\s*Forwarded message\s*$"),

    # Bulgarian (ABV / others)
    re.compile(r"(?im)^\s*>?\s*-+\s*Оригинално писмо\s*-+\s*$"),
    re.compile(r"(?im)^\s*>?\s*Препратено съобщение\s*$"),  # "Forwarded message" (BG)

    # Apple Mail sometimes: "Begin forwarded message:" (already covered), also:
    re.compile(r"(?im)^\s*>?\s*Begin forwarded message:\s*$"),

    # Proton / Fastmail / some clients: "-----Original Message-----" with varying dashes
    re.compile(r"(?im)^\s*>?\s*-{2,}\s*Original Message\s*-{2,}\s*$"),

    # Common "reply header block" starts (From: / Sent: / To: / Subject: / Date:)
    # If we see a header block starter, cut there (covers Outlook Web, many clients).
    re.compile(r"(?im)^\s*>?\s*From:\s+"),
    re.compile(r"(?im)^\s*>?\s*Sent:\s+"),
    re.compile(r"(?im)^\s*>?\s*To:\s+"),
    re.compile(r"(?im)^\s*>?\s*Subject:\s+"),
    re.compile(r"(?im)^\s*>?\s*Date:\s+"),

    # Bulgarian header block (ABV, etc.)
    re.compile(r"(?im)^\s*>?\s*От:\s+"),
    re.compile(r"(?im)^\s*>?\s*До:\s+"),
    re.compile(r"(?im)^\s*>?\s*Относно:\s+"),
    re.compile(r"(?im)^\s*>?\s*Изпратено на:\s+"),

    # Thunderbird / many clients
    re.compile(r"(?im)^\s*>?\s*-----+\s*Forwarded Message\s*-----+\s*$"),
]


# "On ... wrote:" family, localized variants:
# We allow:
# - "On ... wrote:" on same line
# - "On ..." then next line contains "wrote:"
# - localized "wrote" equivalents
_WROTE_WORDS = [
    r"wrote:",         # EN
    r"schrieb:",       # DE
    r"écrit\s*:",      # FR
    r"escribió\s*:",   # ES
    r"ha scritto\s*:", # IT
    r"escreveu\s*:",   # PT
    r"schreef\s*:",    # NL
    r"napisał\s*\(?a\)?\s*:",  # PL (napisał/napisała:)
    r"писал[а]?\s*:",  # RU (писал/писала:)
    r"έγραψε\s*:",     # EL (Greek)
]

# Additional localized "On ..." starters:
_ON_WORDS = [
    r"On",     # EN
    r"Am",     # DE (Am ... schrieb:)
    r"Le",     # FR (Le ... a écrit :)
    r"El",     # ES (El ... escribió :)
    r"Il",     # IT (Il ... ha scritto :)
    r"Em",     # PT (Em ... escreveu :)
    r"Op",     # NL (Op ... schreef :)
    r"W dniu", # PL (W dniu ... napisał(a):)
    r"В",      # RU (В ... писал(а):)
    r"Στις",   # EL (Στις ... έγραψε :)
]


def _find_on_wrote_marker_index(text: str) -> Optional[int]:
    """
    Find earliest occurrence of a reply marker of the form:
      <On-word> ... <wrote-word>
    Where:
      - The <On-word> must start a line (optionally with quote prefix > and whitespace)
      - The <wrote-word> may be on the same line OR within the next 1-2 lines
    """
    lines = text.split("\n")
    offsets = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1

    on_re = re.compile(
        r"(?i)^\s*>?\s*(%s)\b" % "|".join(_ON_WORDS)
    )
    wrote_re = re.compile(
        r"(?i)(%s)\s*$" % "|".join(_WROTE_WORDS)
    )

    for i, ln in enumerate(lines):
        if not on_re.search(ln):
            continue

        # same line contains wrote word?
        if wrote_re.search(ln.strip()):
            return offsets[i]

        # next lines contain wrote word?
        for j in (i + 1, i + 2):
            if j < len(lines):
                if wrote_re.search(lines[j].strip()):
                    return offsets[i]

    return None


def extract_latest_reply_text(body_text: str) -> str:
    """
    Extract newest user-written part of an email body per your specification.

    Rules (in order):
      1) Normalize newlines (\r\n -> \n, \r -> \n)
      2) Cut at earliest quoted-history marker:
         - On ... wrote: (and localized variants, split-line variants)
         - -----Original Message-----
         - Begin forwarded message / Forwarded message
         - Header block markers (From:, От:, etc.)
      3) Remove lines where lstrip starts with ">"
      4) Trim + collapse excessive blank lines (\n{3,} -> \n\n)
      5) If empty after step 3, fall back to trimmed top-part (before removing >)
    """
    if body_text is None:
        return ""

    # 1) Normalize newlines
    text = body_text.replace("\r\n", "\n").replace("\r", "\n")

    # 2) Cut at first quoted-history marker (earliest occurrence wins)
    cut_idx = None

    # On ... wrote family (localized)
    on_wrote_idx = _find_on_wrote_marker_index(text)
    if on_wrote_idx is not None:
        cut_idx = on_wrote_idx

    # Other marker lines
    for pat in _MARKER_LINE_PATTERNS:
        m = pat.search(text)
        if m:
            if cut_idx is None or m.start() < cut_idx:
                cut_idx = m.start()

    top_part = text if cut_idx is None else text[:cut_idx]
    top_part_trimmed = top_part.strip()

    # 3) Remove quote-prefixed lines
    kept_lines = []
    for line in top_part.split("\n"):
        if line.lstrip().startswith(">"):
            continue
        kept_lines.append(line)

    cleaned = "\n".join(kept_lines).strip()

    # 4) Collapse excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # 5) Fallback if empty after cleanup (still no history)
    if not cleaned:
        fallback = re.sub(r"\n{3,}", "\n\n", top_part_trimmed)
        return fallback

    return cleaned