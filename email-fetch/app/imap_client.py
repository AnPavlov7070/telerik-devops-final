import contextlib
from datetime import datetime, timedelta, timezone
from typing import Generator, Iterable, List, Tuple

from imapclient import IMAPClient, exceptions as imap_exceptions

from app.utils import to_imap_date


class ImapUpstreamError(RuntimeError):
    """Raised when upstream IMAP server operations fail."""


class ImapService:
    """
    A thin wrapper around IMAPClient for robust connection, search and fetch.
    """

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        username: str,
        password: str,
        folder: str,
    ):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.folder = folder

    @contextlib.contextmanager
    def connect_and_login(self) -> Generator[IMAPClient, None, None]:
        try:
            client = IMAPClient(self.host, port=self.port, ssl=self.use_ssl)
            client.login(self.username, self.password)
            client.select_folder(self.folder, readonly=True)
            yield client
        except imap_exceptions.IMAPClientError as e:
            raise ImapUpstreamError(str(e)) from e
        finally:
            with contextlib.suppress(Exception):
                client.logout()

    def search_uids_in_date_window(
        self, client: IMAPClient, since: datetime, until: datetime
    ) -> List[int]:
        """
        IMAP SEARCH supports only dates (no time). Use SINCE (inclusive) and BEFORE (exclusive)
        to narrow down, then filter precisely after fetching by INTERNALDATE.

        We use:
          SINCE since.date()
          BEFORE (until.date() + 1 day)
        """
        try:
            since_date = to_imap_date(since)
            before_date = to_imap_date((until + timedelta(days=1)))
            # Build criteria per IMAPClient format
            criteria = ["SINCE", since_date, "BEFORE", before_date]
            uids = client.search(criteria)
            # Return ascending order for determinism
            return sorted(uids)
        except imap_exceptions.IMAPClientError as e:
            raise ImapUpstreamError(str(e)) from e

    def fetch_rfc822_and_internaldate(
        self, client: IMAPClient, uids: Iterable[int]
    ) -> Iterable[Tuple[int, bytes, datetime]]:
        """
        Fetch RFC822 (raw bytes) and INTERNALDATE for each UID.
        Yields (uid, raw_bytes, internaldate_utc).
        """
        if not uids:
            return []

        try:
            response = client.fetch(uids, ["RFC822", "INTERNALDATE"])
        except imap_exceptions.IMAPClientError as e:
            raise ImapUpstreamError(str(e)) from e

        out = []
        for uid in uids:
            msg = response.get(uid)
            if not msg:
                continue
            raw: bytes = msg.get(b"RFC822") or msg.get("RFC822")
            internal: datetime = msg.get(b"INTERNALDATE") or msg.get("INTERNALDATE")
            if raw is None or internal is None:
                continue
            # INTERNALDATE is timezone-aware; normalize to UTC
            if internal.tzinfo is None:
                internal = internal.replace(tzinfo=timezone.utc)
            internal_utc = internal.astimezone(timezone.utc)
            out.append((uid, raw, internal_utc))
        return out
