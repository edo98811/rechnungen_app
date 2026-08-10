# Update the login password on the Raspberry Pi deployment

## Summary
User needed to know how to rotate the login password on the Pi deployment.
The repo's `docker-compose.pi.yml` didn't match what's actually deployed on
the Pi, so the initial `docker compose run` command targeted the wrong
service name. Resolved by inspecting the Pi's real compose file.

## Timeline

- **Explained password rotation mechanism**
  Read `app/auth.py`: `AUTH_PASSWORD_HASH` in `.env` is a pbkdf2_sha256
  hash, not plaintext. The file's `__main__` block prompts for a password
  and prints the hash to store.
  Decision: rotate by generating a new hash via `python -m app.auth` inside
  the deployed container, updating `.env`, and recreating the container.

- **Proposed initial command based on repo's `docker-compose.pi.yml`**
  ```
  docker compose -f docker-compose.pi.yml run --rm backend python -m app.auth
  ```
  Decision: assumed service name `backend`, matching the repo file's
  `services: backend:` block.

- **User ran the equivalent command on the Pi and hit an error**
  ```
  docker compose -f docker-compose.yml run --rm backend python -m app.auth
  ```
  Result: `no such service: backend`
  Decision: the compose file actually deployed on the Pi doesn't match the
  repo's `docker-compose.pi.yml` — asked user to paste the real file and
  `docker compose ps`.

- **Inspected the Pi's actual `docker-compose.yml`**
  ```
  cat docker-compose.yml
  ```
  Result: service is named `rechnungen` (not `backend`), image
  `ghcr.io/edo98811/rechnungen:latest`, volume mounted at
  `/mnt/storage/appdata/rechnungen:/data` (repo file uses a named Docker
  volume `data:/app/data`), attached to external network `proxy-net`
  (repo file has no network), and has no top-level `name:` (repo file sets
  `name: rechnungen`) or `ports:` mapping (Pi's is presumably reverse-proxied
  via `proxy-net` instead of a direct port).
  Decision: corrected the command to use service name `rechnungen`.

## Root cause / what was needed
The repo's `docker-compose.pi.yml` has drifted from the compose file
actually running on the Pi (`~/infra/rechnungen/docker-compose.yml`) —
different service name (`rechnungen` vs `backend`), volume target, and
networking setup. The correct password-rotation command for the real
deployment is:
```
docker compose -f docker-compose.yml run --rm rechnungen python -m app.auth
docker compose -f docker-compose.yml up -d --force-recreate rechnungen
```

## Final state
No files changed. User has the correct commands to rotate the Pi's login
password.

## Follow-ups
- `docker-compose.pi.yml` in the repo should be reconciled with the actual
  Pi deployment file (service name, volume path, `proxy-net` network,
  absence of a direct port mapping) so it's an accurate reference going
  forward.
