"""FastAPI server for the library web app, behind PRJ012's login.

Routing: the app serves everything under `/library` itself and nginx does NOT
strip that prefix (`proxy_pass http://127.0.0.1:8731;` without a URI part).
Auth contract (spec section 6b): the browser sends `Authorization: Bearer
<supabase access token>`; this server never verifies JWTs, it asks PRJ012
`/api/v1/me/permissions` (and `/api/v1/me` for the author name) with that
same header, and caches the answer per token hash for at most 60 s.
Tokens are never logged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from wing_parser import config
from wing_parser.library import (
    LibraryStore,
    EntryExists,
    RevisionConflict,
    ValidationFailed,
    facets,
    load_topics,
)
from wing_parser.library import schema
from wing_parser.library.web import render
from wing_parser.library.web.export import static_text

log = logging.getLogger("wing_library_web")
AUTH_BASE_DEFAULT = "https://master.azsoundtech.com"
VIEW, EDIT = "knowledge_library.view", "knowledge_library.edit"
CACHE_TTL = 60.0
CACHE_MAX = 256
STATIC_FILES = {"app.js": "text/javascript", "app.css": "text/css"}
CSP = ("default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; connect-src 'self'; frame-src https://www.youtube-nocookie.com; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'self'")


class Upstream(Exception):
    """PRJ012 could not be reached (network error or timeout)."""


def _http_get_json(url: str, token: str, timeout: float = 5.0) -> tuple[int, object, str]:
    """GET with the user's bearer token -> (status, parsed json or None, raw text)."""
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (configured https base)
            status, raw = response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Upstream(type(exc).__name__) from None
    try:
        return status, json.loads(raw), raw
    except ValueError:
        return status, None, raw


class AuthClient:
    """Asks PRJ012 who the caller is; bounded per-token-hash cache (<= 60 s)."""

    def __init__(self, base: str, *, ttl: float = CACHE_TTL, max_items: int = CACHE_MAX, clock=time.monotonic):
        self.base = base.rstrip("/")
        self.ttl, self.max_items, self.clock = ttl, max_items, clock
        self._cache: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def _cached(self, kind: str, token: str, fetch):
        key = f"{kind}:{hashlib.sha256(token.encode()).hexdigest()}"
        now = self.clock()
        with self._lock:
            hit = self._cache.get(key)
            if hit and hit[0] > now:
                return hit[1]
        value = fetch()
        with self._lock:
            self._cache[key] = (now + self.ttl, value)
            for stale in [k for k, (until, _) in self._cache.items() if until <= now]:
                del self._cache[stale]
            while len(self._cache) > self.max_items:
                del self._cache[next(iter(self._cache))]
        return value

    def _get(self, path: str, token: str):
        try:
            return _http_get_json(f"{self.base}{path}", token)
        except Upstream:
            raise HTTPException(503, "auth_unavailable") from None

    def permissions(self, token: str) -> dict[str, bool]:
        def fetch() -> dict[str, bool]:
            status, body, raw = self._get(f"/api/v1/me/permissions?codes={VIEW},{EDIT}", token)
            if status == 401:
                raise HTTPException(401, "unauthenticated")
            if status == 422:  # bad `codes` = our bug, not the caller's: log the code, never the token
                code = "bad_payload" if "bad_payload" in raw else "unknown"
                log.error("PRJ012 permissions rejected our request: 422 %s", code)
                raise HTTPException(502, "auth_bad_request")
            if status == 404 and "not_linked" in raw:
                return {VIEW: False, EDIT: False}
            if status != 200 or not isinstance(body, dict) or not isinstance(body.get("permissions"), dict):
                raise HTTPException(503, "auth_unavailable")
            granted = body["permissions"]
            return {VIEW: granted.get(VIEW) is True, EDIT: granted.get(EDIT) is True}
        return self._cached("perm", token, fetch)

    def member(self, token: str) -> dict[str, str]:
        def fetch() -> dict[str, str]:
            status, body, _ = self._get("/api/v1/me", token)
            if status == 401:
                raise HTTPException(401, "unauthenticated")
            if status != 200 or not isinstance(body, dict) or not body.get("member_id"):
                raise HTTPException(503, "auth_unavailable")
            name = " ".join(str(body.get("display_name") or "member").split())[:80]
            return {"display_name": name, "member_id": str(body["member_id"]),
                    "author": f"{name} (prj012:{body['member_id']})"}
        return self._cached("me", token, fetch)


def _token(authorization: str | None) -> str:
    scheme, _, value = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise HTTPException(401, "unauthenticated")
    return value.strip()


def _opt_int(value) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        raise HTTPException(422, "revision_invalid") from None


def _issues(items) -> list[dict]:
    return [i.__dict__ for i in items]


def create_app(store: LibraryStore | None = None, *, auth_base: str | None = None,
               prefix: str = "/library") -> FastAPI:
    store = store or LibraryStore(config.library_dir(), Path(
        os.environ.get("WING_LIBRARY_SHIPPED_DIR") or config.shipped_library_dir()))
    auth = AuthClient(auth_base or os.environ.get("WING_LIBRARY_AUTH_BASE") or AUTH_BASE_DEFAULT)
    write_lock = threading.Lock()
    app = FastAPI(title="wing-library-web", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.auth, app.state.store = auth, store
    router = APIRouter(prefix=prefix)

    def need_view(authorization: str | None = Header(None)) -> str:
        token = _token(authorization)
        if not auth.permissions(token)[VIEW]:
            raise HTTPException(403, "forbidden")
        return token

    def need_edit(authorization: str | None = Header(None)) -> str:
        token = _token(authorization)
        perms = auth.permissions(token)
        if not (perms[VIEW] and perms[EDIT]):
            raise HTTPException(403, "forbidden")
        return token

    def entry_or_404(entry_id: str):
        if not schema.ID_RE.match(entry_id):
            raise HTTPException(404, "not_found")
        try:
            return store.get(entry_id)
        except KeyError:
            raise HTTPException(404, "not_found") from None

    def clean(payload: dict) -> dict:
        entry = payload.get("entry")
        if not isinstance(entry, dict):
            raise HTTPException(422, "entry_required")
        return {k: v for k, v in entry.items() if k in render.EDITABLE_KEYS}

    def note_of(payload: dict, *, required: bool) -> str:
        note = str(payload.get("note") or "").strip()
        if required and not note:
            raise HTTPException(422, "note_required")
        return note

    def write(fn):
        try:
            with write_lock:
                return fn()
        except ValidationFailed as exc:
            return JSONResponse({"detail": "validation", "issues": _issues(exc.issues)}, 422)
        except EntryExists:
            return JSONResponse({"detail": "exists"}, 409)
        except RevisionConflict as exc:
            return JSONResponse({"detail": "revision_conflict", "expected": exc.expected,
                                 "actual": exc.actual}, 409)
        except KeyError:
            raise HTTPException(404, "not_found") from None

    def saved(entry_id: str) -> dict:
        return render.detail(store.get(entry_id), media_prefix="api/media/", raw=True)

    # -- shell and assets (no data, no auth) --------------------------------
    @router.get("/healthz")
    def healthz():
        return {"ok": True}

    @router.get("/")
    def shell():
        return HTMLResponse(static_text("index.html"), headers={"Content-Security-Policy": CSP,
                                                                 "Cache-Control": "no-cache"})

    @router.get("/static/{name}")
    def static(name: str):
        if name not in STATIC_FILES:
            raise HTTPException(404, "not_found")
        return Response(static_text(name), media_type=STATIC_FILES[name],
                        headers={"Cache-Control": "no-cache"})

    # -- reads --------------------------------------------------------------
    @router.get("/api/me")
    def me(token: str = Depends(need_view)):
        can_edit = auth.permissions(token)[EDIT]
        name = auth.member(token)["display_name"] if can_edit else ""
        return {"display_name": name, "can_edit": can_edit}

    @router.get("/api/entries")
    def entries(token: str = Depends(need_view)):
        loaded = store.entries(include_retired=True)
        return {"mode": "server", "can_edit": auth.permissions(token)[EDIT],
                "topics": render.topic_list(load_topics(store.taxonomy_root)),
                "schema": render.schema_info(),
                "entries": [render.list_item(x) for x in loaded],
                "facets": {k: dict(v) for k, v in facets(loaded).items()}}

    @router.get("/api/entries/{entry_id}")
    def entry(entry_id: str, token: str = Depends(need_view)):
        return render.detail(entry_or_404(entry_id), media_prefix="api/media/", raw=True)

    @router.get("/api/media/{entry_id}/{file:path}")
    def media(entry_id: str, file: str, token: str = Depends(need_view)):
        if not schema.ID_RE.match(entry_id) or not file.lower().endswith(".png"):
            raise HTTPException(404, "not_found")
        try:
            path = store.media_file(entry_id, file)
        except ValueError:
            raise HTTPException(404, "not_found") from None
        if path is None or not path.is_file():
            raise HTTPException(404, "not_found")
        return FileResponse(path, media_type="image/png",
                            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300"})

    @router.get("/api/entries/{entry_id}/history")
    def history(entry_id: str, token: str = Depends(need_view)):
        entry_or_404(entry_id)
        revisions, skipped = store.history_report(entry_id)
        return {"skipped": skipped,
                "revisions": [{"rev": r.rev, "at": r.at, "author": r.author, "action": r.action,
                               "note": r.note} for r in revisions]}

    @router.get("/api/entries/{entry_id}/diff")
    def diff(entry_id: str, a: int = Query(...), b: int = Query(...), token: str = Depends(need_view)):
        entry_or_404(entry_id)
        try:
            return {"diff": store.diff(entry_id, a, b)}
        except KeyError:
            raise HTTPException(404, "not_found") from None

    # -- writes (need knowledge_library.edit; author comes from PRJ012) -----
    @router.post("/api/entries")
    def create(payload: dict = Body(...), token: str = Depends(need_edit)):
        entry = clean(payload)
        author = auth.member(token)["author"]
        entry_id = str(entry.get("id", ""))
        note = note_of(payload, required=False) or "created"
        return write(lambda: (store.save(entry, author=author, note=note, create=True),
                              saved(entry_id))[1])

    @router.put("/api/entries/{entry_id}")
    def edit(entry_id: str, payload: dict = Body(...), token: str = Depends(need_edit)):
        entry_or_404(entry_id)
        entry = clean(payload)
        entry["id"] = entry_id
        try:
            revision = int(payload.get("revision"))
        except (TypeError, ValueError):
            raise HTTPException(422, "revision_required") from None
        note = note_of(payload, required=True)
        author = auth.member(token)["author"]
        return write(lambda: (store.save(entry, author=author, note=note, expected_revision=revision),
                              saved(entry_id))[1])

    @router.post("/api/entries/{entry_id}/retire")
    def retire(entry_id: str, payload: dict = Body(default={}), token: str = Depends(need_edit)):
        entry_or_404(entry_id)
        author = auth.member(token)["author"]
        note = note_of(payload, required=False)
        expected = _opt_int(payload.get("revision"))
        return write(lambda: (store.retire(entry_id, author=author, note=note,
                                           expected_revision=expected), saved(entry_id))[1])

    @router.post("/api/entries/{entry_id}/restore")
    def restore(entry_id: str, payload: dict = Body(...), token: str = Depends(need_edit)):
        entry_or_404(entry_id)
        try:
            rev = int(payload.get("rev"))
        except (TypeError, ValueError):
            raise HTTPException(422, "rev_required") from None
        author = auth.member(token)["author"]
        note = note_of(payload, required=False)
        expected = _opt_int(payload.get("revision"))
        return write(lambda: (store.restore(entry_id, rev, author=author, note=note,
                                            expected_revision=expected), saved(entry_id))[1])

    app.include_router(router)
    if prefix:
        app.add_api_route(prefix, lambda: RedirectResponse(f"{prefix}/", 307), include_in_schema=False)
    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wing-library-web",
                                     description="Mixing knowledge library web server (behind PRJ012 login)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8731)
    args = parser.parse_args(argv)
    try:
        render.markdown_module()
        import uvicorn
    except (render.MissingDependency, ImportError) as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
