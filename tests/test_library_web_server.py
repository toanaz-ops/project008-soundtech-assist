"""Server mode with PRJ012 monkeypatched: auth contract, writes, caching."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("markdown")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from tests.library_support import entry, make_root  # noqa: E402
from wing_parser.library import LibraryStore  # noqa: E402
from wing_parser.library.web import server  # noqa: E402

FAKE = "fake-token-not-a-secret"
ME = {"member_id": 42, "display_name": "Test  Member", "is_owner": False}
PERMS = {"view": {server.VIEW: True, server.EDIT: False}, "edit": {server.VIEW: True, server.EDIT: True}}


class Prj012:
    """Stands in for PRJ012; records every call as (path, token)."""

    def __init__(self):
        self.mode, self.calls = "edit", []

    def __call__(self, url, token, timeout=5.0):
        path = url.split("master.test", 1)[1]
        self.calls.append((path, token))
        if self.mode == "401":
            return 401, {"detail": "bad token"}, "{}"
        if self.mode == "down":
            raise server.Upstream("URLError")
        if path.startswith("/api/v1/me/permissions"):
            assert "codes=knowledge_library.view,knowledge_library.edit" in path
            if self.mode == "not_linked":
                return 404, {"error": "not_linked"}, '{"error":"not_linked"}'
            if self.mode == "422":
                return 422, {"error": "bad_payload"}, '{"error":"bad_payload"}'
            return 200, {"permissions": PERMS[self.mode]}, "{}"
        if path == "/api/v1/me":
            return 200, ME, "{}"
        raise AssertionError(path)


@pytest.fixture
def prj(monkeypatch):
    fake = Prj012()
    monkeypatch.setattr(server, "_http_get_json", fake)
    return fake


@pytest.fixture
def store(tmp_path):
    s = LibraryStore(make_root(tmp_path / "user"), None)
    s.save(entry("hpf-basics"), author="seed", note="seed")
    media = tmp_path / "user" / "media" / "hpf-basics"
    media.mkdir(parents=True)
    (media / "d.png").write_bytes(b"\x89PNG\r\n\x1a\n0000")
    return s


@pytest.fixture
def client(store, prj):
    return TestClient(server.create_app(store, auth_base="https://master.test"))


def auth(token=FAKE):
    return {"Authorization": f"Bearer {token}"}


def body(revision=1):
    return {"entry": entry("hpf-basics", title="Changed title"), "revision": revision, "note": "tweak"}


def test_healthz_and_shell_need_no_auth(client, prj):
    assert client.get("/library/healthz").json() == {"ok": True}
    shell = client.get("/library/")
    assert shell.status_code == 200 and 'id="library-data"' not in shell.text
    assert "script-src 'self'" in shell.headers["content-security-policy"]
    assert client.get("/library/static/app.js").status_code == 200
    assert client.get("/library/static/secret.txt").status_code == 404
    assert prj.calls == []


def test_no_token_is_401_and_makes_no_upstream_call(client, prj):
    assert client.get("/library/api/entries").status_code == 401
    assert client.get("/library/api/entries", headers={"Authorization": "Basic x"}).status_code == 401
    assert prj.calls == []


def test_upstream_401_is_401(client, prj):
    prj.mode = "401"
    assert client.get("/library/api/entries", headers=auth()).status_code == 401


def test_view_only_can_read_not_write(client, prj):
    prj.mode = "view"
    listing = client.get("/library/api/entries", headers=auth())
    assert listing.status_code == 200 and listing.json()["can_edit"] is False
    assert [e["id"] for e in listing.json()["entries"]] == ["hpf-basics"]
    assert client.get("/library/api/entries/hpf-basics", headers=auth()).json()["body"]
    assert client.get("/library/api/me", headers=auth()).json() == {"display_name": "", "can_edit": False}
    assert client.put("/library/api/entries/hpf-basics", json=body(), headers=auth()).status_code == 403
    assert client.post("/library/api/entries", json=body(), headers=auth()).status_code == 403
    assert client.post("/library/api/entries/hpf-basics/retire", json={}, headers=auth()).status_code == 403
    assert client.post("/library/api/entries/hpf-basics/restore", json={"rev": 1},
                       headers=auth()).status_code == 403


def test_edit_writes_with_author_from_prj012_not_the_client(client, store):
    payload = body()
    payload["entry"]["updated_by"] = "attacker"
    res = client.put("/library/api/entries/hpf-basics", json=payload, headers=auth())
    assert res.status_code == 200, res.text
    assert res.json()["revision"] == 2 and res.json()["title"] == "Changed title"
    assert store.get("hpf-basics").entry["updated_by"] == "Test Member (prj012:42)"
    history = client.get("/library/api/entries/hpf-basics/history", headers=auth()).json()["revisions"]
    assert history[-1]["author"] == "Test Member (prj012:42)" and history[-1]["note"] == "tweak"
    diff = client.get("/library/api/entries/hpf-basics/diff?a=1&b=2", headers=auth())
    assert diff.status_code == 200 and "Changed title" in diff.json()["diff"]
    assert client.get("/library/api/me", headers=auth()).json()["can_edit"] is True


def test_not_linked_is_403(client, prj):
    prj.mode = "not_linked"
    assert client.get("/library/api/entries", headers=auth()).status_code == 403


def test_permissions_422_is_502_and_never_logs_the_token(client, prj, caplog):
    prj.mode = "422"
    with caplog.at_level("DEBUG"):
        res = client.get("/library/api/entries", headers=auth())
    assert res.status_code == 502
    assert "bad_payload" in caplog.text and FAKE not in caplog.text


def test_upstream_down_is_503(client, prj):
    prj.mode = "down"
    assert client.get("/library/api/entries", headers=auth()).status_code == 503


def test_revision_conflict_is_409(client):
    res = client.put("/library/api/entries/hpf-basics", json=body(revision=7), headers=auth())
    assert res.status_code == 409 and res.json()["actual"] == 1


def test_unsourced_create_is_422_with_issues(client, store):
    new = entry("fresh-entry", sources=[])
    res = client.post("/library/api/entries", json={"entry": new, "note": "x"}, headers=auth())
    assert res.status_code == 422
    assert any(i["code"] == "unsourced" for i in res.json()["issues"])
    with pytest.raises(KeyError):
        store.get("fresh-entry")


def test_create_then_duplicate_and_note_required(client):
    ok = client.post("/library/api/entries", json={"entry": entry("fresh-entry"), "note": ""}, headers=auth())
    assert ok.status_code == 200 and ok.json()["revision"] == 1
    dup = client.post("/library/api/entries", json={"entry": entry("fresh-entry"), "note": ""}, headers=auth())
    assert dup.status_code == 409
    no_note = body()
    no_note["note"] = " "
    assert client.put("/library/api/entries/hpf-basics", json=no_note, headers=auth()).status_code == 422


def test_retire_and_restore(client):
    retired = client.post("/library/api/entries/hpf-basics/retire", json={"note": "old"}, headers=auth())
    assert retired.json()["status"] == "retired"
    back = client.post("/library/api/entries/hpf-basics/restore", json={"rev": 1}, headers=auth())
    assert back.status_code == 200 and back.json()["status"] == "draft" and back.json()["revision"] == 3


def test_media_requires_auth_and_blocks_traversal(client, prj):
    assert client.get("/library/api/media/hpf-basics/d.png").status_code == 401
    ok = client.get("/library/api/media/hpf-basics/d.png", headers=auth())
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    assert client.get("/library/api/media/hpf-basics/..%2F..%2Ftopics.yaml", headers=auth()).status_code == 404
    assert client.get("/library/api/media/hpf-basics/missing.png", headers=auth()).status_code == 404


def test_permission_result_is_cached_per_token(client, prj):
    for _ in range(3):
        assert client.get("/library/api/entries", headers=auth()).status_code == 200
    assert len([c for c in prj.calls if c[0].startswith("/api/v1/me/permissions")]) == 1
    client.get("/library/api/entries", headers=auth("another-fake-token"))
    assert len(prj.calls) == 2


def test_cache_expires_and_is_bounded(prj):
    now = [0.0]
    auth_client = server.AuthClient("https://master.test", ttl=60, max_items=3, clock=lambda: now[0])
    auth_client.permissions("t1")
    auth_client.permissions("t1")
    assert len(prj.calls) == 1
    now[0] = 61.0
    auth_client.permissions("t1")
    assert len(prj.calls) == 2
    for n in range(10):
        auth_client.permissions(f"tok{n}")
    assert len(auth_client._cache) <= 3


def test_retire_a_broken_entry_and_stale_revision_is_409(client, store):
    (store.root / "entries" / "hand-made.yaml").write_text(
        "id: hand-made\nrevision: 1\ntitle: x\n", encoding="utf-8")
    stale = client.post("/library/api/entries/hand-made/retire", json={"revision": 5}, headers=auth())
    assert stale.status_code == 409
    ok = client.post("/library/api/entries/hand-made/retire", json={"revision": 1}, headers=auth())
    assert ok.status_code == 200 and ok.json()["status"] == "retired"
    stale_restore = client.post("/library/api/entries/hpf-basics/restore",
                                json={"rev": 1, "revision": 9}, headers=auth())
    assert stale_restore.status_code == 409


def test_create_over_a_hand_written_file_is_409_and_history_survives_a_bad_line(client, store):
    (store.root / "entries" / "hand-made.yaml").write_text(
        "id: hand-made\nrevision: 1\n", encoding="utf-8")
    res = client.post("/library/api/entries", json={"entry": entry("hand-made"), "note": ""}, headers=auth())
    assert res.status_code == 409 and res.json()["detail"] == "exists"
    with open(store.root / "history" / "hpf-basics.jsonl", "a", encoding="utf-8") as handle:
        handle.write('{"rev": 2, "at"')
    hist = client.get("/library/api/entries/hpf-basics/history", headers=auth())
    assert hist.status_code == 200 and hist.json()["skipped"] == 1
    assert client.put("/library/api/entries/hpf-basics", json=body(), headers=auth()).status_code == 200


def test_csp_forbids_framing(client):
    assert "frame-ancestors 'self'" in server.CSP
    assert "frame-ancestors" in client.get("/library/").headers["content-security-policy"]
