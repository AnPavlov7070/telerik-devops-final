from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class FetchRequest(BaseModel):
    since: datetime = Field(..., description="ISO-8601 UTC timestamp inclusive")
    until: datetime = Field(..., description="ISO-8601 UTC timestamp inclusive")

    @field_validator("since", "until")
    @classmethod
    def enforce_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Timestamp must include timezone and be in UTC (e.g., ...Z)")
        # Normalize to UTC
        return v.astimezone(tz=None).astimezone(tz=v.tzinfo)

    @property
    def since_iso(self) -> str:
        return self.since.astimezone(tz=None).astimezone().isoformat()

    @property
    def until_iso(self) -> str:
        return self.until.astimezone(tz=None).astimezone().isoformat()


class AttachmentMeta(BaseModel):
    filename: Optional[str] = None
    contentType: Optional[str] = None
    size: Optional[int] = None


class EmailItem(BaseModel):
    messageId: str
    subject: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    to: List[str] = []
    cc: List[str] = []
    date: Optional[str] = None  # ISO-8601 UTC
    receivedAt: str  # ISO-8601 UTC from INTERNALDATE
    snippet: Optional[str] = None
    bodyText: Optional[str] = None
    bodyTextLatest: Optional[str] = None
    hasHtml: bool = False
    attachmentsMeta: List[AttachmentMeta] = []
    dealId: Optional[str] = None

    # Non-serialized helper to compute max easily
    @property
    def receivedAt_dt(self) -> datetime:
        return datetime.fromisoformat(self.receivedAt.replace("Z", "+00:00"))


class FetchResponse(BaseModel):
    mostRecentReceivedAt: Optional[str]
    count: int
    items: List[EmailItem] = []
