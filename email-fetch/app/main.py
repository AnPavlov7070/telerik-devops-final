import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.imap_client import ImapService, ImapUpstreamError
from app.models import FetchRequest, FetchResponse, EmailItem
from app.parser import parse_email_bytes_to_item
from app.state import StateStore
from app.utils import max_iso

logger = logging.getLogger("app.main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="Email Fetch Service", version="1.0.0")


@app.post("/fetch", response_model=FetchResponse)
def fetch_emails(req: FetchRequest):
    """
    Fetch emails in the inclusive [since, until] time window based on IMAP INTERNALDATE.
    Deduplicate against previously-seen message identifiers, persist state atomically,
    and return the current batch plus the most recent receivedAt.
    """
    settings: Settings = get_settings()

    if req.since > req.until:
        raise HTTPException(status_code=400, detail="since must be <= until")

    try:
        state = StateStore(settings.STATE_PATH)
        imap = ImapService(
            host=settings.IMAP_HOST,
            port=settings.IMAP_PORT,
            use_ssl=settings.IMAP_SSL,
            username=settings.IMAP_USERNAME,
            password=settings.IMAP_PASSWORD,
            folder=settings.IMAP_FOLDER,
        )

        logger.info(
            "fetch_start",
            extra={
                "since": req.since_iso,
                "until": req.until_iso,
                "folder": settings.IMAP_FOLDER,
                "host": settings.IMAP_HOST,
            },
        )

        with imap.connect_and_login() as client:
            uids = imap.search_uids_in_date_window(client, req.since, req.until)
            logger.info("imap_search_done", extra={"candidate_count": len(uids)})

            items: List[EmailItem] = []
            newly_seen_keys: List[str] = []

            for uid, raw, internaldate in imap.fetch_rfc822_and_internaldate(client, uids):
                try:
                    item, identity_key = parse_email_bytes_to_item(raw, internaldate)
                except Exception as e:  # parsing error shouldn't break the whole batch
                    logger.exception("parse_error", extra={"uid": uid})
                    continue

                if state.is_seen(identity_key):
                    logger.info("skip_duplicate", extra={"identity": identity_key})
                    continue

                # filter precisely by INTERNALDATE in UTC outside IMAP search limitation
                if not (req.since <= item.receivedAt_dt <= req.until):
                    logger.info(
                        "skip_outside_window",
                        extra={
                            "identity": identity_key,
                            "receivedAt": item.receivedAt,
                            "since": req.since_iso,
                            "until": req.until_iso,
                        },
                    )
                    continue

                items.append(item)
                newly_seen_keys.append(identity_key)

            # persist state atomically with a simple lock
            state.add_many(newly_seen_keys)

            most_recent = max_iso([i.receivedAt for i in items])
            resp = FetchResponse(
                mostRecentReceivedAt=most_recent,
                count=len(items),
                items=items,
            )
            logger.info(
                "fetch_done",
                extra={"returned_count": len(items), "most_recent": most_recent},
            )
            return JSONResponse(resp.model_dump())
    except ImapUpstreamError as e:
        logger.exception("imap_upstream_error")
        raise HTTPException(
            status_code=502,
            detail={"error": "upstream_imap_error", "detail": str(e)},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("internal_error")
        raise HTTPException(status_code=500, detail="internal_server_error")
    
    #test1
