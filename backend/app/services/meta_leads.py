"""Meta Lead Ads (Facebook + Instagram lead forms) over the Graph API.

Flow: Meta POSTs a `leadgen` change to /api/integrations/meta/webhook when someone
submits a lead form on a connected Page (forms in Instagram ads belong to the Page
too). The change only carries ids, so the lead itself is fetched with the Page
access token. "Sync now" pulls a Page's form leads in bulk the same way.

All HTTP calls live here so tests can replace them.
"""

import hashlib
import hmac
import logging
from collections.abc import Iterator
from datetime import datetime

import httpx

from app.core.config import settings

logger = logging.getLogger("nexa_crm")

GRAPH_URL = "https://graph.facebook.com"
TIMEOUT = httpx.Timeout(15.0)
LEAD_FIELDS = "id,created_time,field_data,platform,form_id,ad_name,campaign_name"
# `platform` isn't available on every API version/lead; retried without it on "unknown field".
BASIC_LEAD_FIELDS = "id,created_time,field_data,form_id,ad_name,campaign_name"
# New leads imported by one "Sync now"; the rest come with the next one.
MAX_SYNC_LEADS = 2000


class MetaError(Exception):
    """The Graph API refused or failed a request. The message is Meta's, safe to show to admins."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def _url(path: str) -> str:
    return f"{GRAPH_URL}/{settings.meta_graph_version}/{path.lstrip('/')}"


def _request(method: str, url: str, token: str, params: dict | None = None) -> dict:
    try:
        response = httpx.request(method, url, params={**(params or {}), "access_token": token}, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise MetaError(f"Couldn't reach Meta: {exc.__class__.__name__}") from exc
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.is_error or "error" in data:
        error = data.get("error") or {}
        raise MetaError(error.get("message") or f"Meta returned HTTP {response.status_code}", error.get("code"))
    return data


def get_page(page_id: str, token: str) -> dict:
    """{id, name} of the Page; checks that the token can read it."""
    return _request("GET", _url(page_id), token, {"fields": "id,name"})


def subscribe_page(page_id: str, token: str) -> None:
    """Install the app on the Page for `leadgen` webhooks (needs pages_manage_metadata)."""
    _request("POST", _url(f"{page_id}/subscribed_apps"), token, {"subscribed_fields": "leadgen"})


def get_lead(leadgen_id: str, token: str) -> dict:
    try:
        return _request("GET", _url(leadgen_id), token, {"fields": LEAD_FIELDS})
    except MetaError as exc:
        if exc.code != 100:
            raise
        return _request("GET", _url(leadgen_id), token, {"fields": BASIC_LEAD_FIELDS})


def _paged(url: str, token: str, params: dict) -> Iterator[dict]:
    data = _request("GET", url, token, params)
    while True:
        yield from data.get("data", [])
        next_url = (data.get("paging") or {}).get("next")
        if not next_url:
            return
        # `next` already carries every query parameter, including the token.
        try:
            response = httpx.get(next_url, timeout=TIMEOUT)
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MetaError(f"Couldn't read the next page from Meta: {exc.__class__.__name__}") from exc
        if "error" in data:
            raise MetaError(data["error"].get("message") or "Meta returned an error", data["error"].get("code"))


def iter_page_leads(page_id: str, token: str, since: datetime | None = None) -> Iterator[dict]:
    """Every lead of every lead form on the Page, newest forms first, created after `since`.

    Lazy: the caller stops reading when it has enough (see MAX_SYNC_LEADS), and later pages aren't fetched.
    """
    params: dict = {"fields": LEAD_FIELDS, "limit": 100}
    if since is not None:
        params["filtering"] = f'[{{"field":"time_created","operator":"GREATER_THAN","value":{int(since.timestamp())}}}]'
    for form in _paged(_url(f"{page_id}/leadgen_forms"), token, {"fields": "id,name", "limit": 100}):
        for lead in _paged(_url(f"{form['id']}/leads"), token, params):
            lead.setdefault("form_name", form.get("name"))
            yield lead


def lead_to_row(lead: dict) -> dict:
    """Flatten a Graph API lead into the loose row shape `lead_import.parse_row` understands."""
    row: dict = {}
    for item in lead.get("field_data") or []:
        if item.get("name"):
            row[item["name"]] = item.get("values") or []
    row["leadgen_id"] = lead.get("id")
    if lead.get("platform"):
        row["platform"] = lead["platform"]
    for key, label in (("form_name", "Form"), ("campaign_name", "Campaign"), ("ad_name", "Ad")):
        if lead.get(key):
            row[label] = lead[key]
    return row


def verify_signature(body: bytes, header: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 (HMAC-SHA256 of the raw body with the app secret)."""
    if not settings.meta_app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(settings.meta_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))
