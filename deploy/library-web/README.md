# Library web app on the VPS

`wing-library-web` serves the mixing knowledge library at
`https://master.azsoundtech.com/library/` behind PRJ012's login. The page
shell holds no data; every API call carries the user's PRJ012 bearer token,
and the server asks PRJ012 (`/api/v1/me/permissions`, `/api/v1/me`) what the
caller may do (view / edit, cached up to 60 s). The server never verifies
JWTs and never reads PRJ012's `.env`.

## Build and run

```
git clone <P008 repo> && cd project008-soundtech-assist      # first time
docker compose -f deploy/library-web/docker-compose.yml up -d --build
curl http://127.0.0.1:8731/library/healthz                   # {"ok":true}
```

Then add `nginx-location.conf` to PRJ012's server block and `nginx -t && nginx -s reload`.
The prefix is not stripped: the app itself serves `/library/...`.

Environment (see `docker-compose.yml`): `WING_LIBRARY_DIR` (user layer, the
`library_user` volume), `WING_LIBRARY_SHIPPED_DIR` (shipped layer baked into
the image), `WING_LIBRARY_AUTH_BASE` (PRJ012 base URL).

## Updating

- **Shipped entries** (new/updated library content from the repo): pull the
  new P008 commit and rerun `docker compose ... up -d --build`. Entries the
  web users have edited stay theirs (user layer wins by id); the user volume
  is never touched by a rebuild.
- **Code changes**: same command.

## Bringing web edits back into the repo

Web edits live only in the volume (`/data/library/entries/*.yaml` and
`history/*.jsonl`). Not automatic: an agent (or you) copies them out and opens a PR.

```
docker cp wing-library-web:/data/library ./library-user
git switch -c library/web-edits-YYYYMMDD
cp library-user/entries/*.yaml knowledge/library/entries/
cp library-user/history/*.jsonl knowledge/library/history/
wing library validate --strict
```

Commit, push the branch, open a PR. After it merges and the image is rebuilt,
the shipped layer matches the edits (the user copies then equal shipped).

## Permissions

PRJ012 owns `knowledge_library.view` / `knowledge_library.edit` (default closed,
owner always allowed). No view permission -> 403 on every data route.
