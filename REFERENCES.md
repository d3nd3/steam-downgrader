# External downgrade references

Notes on public recipes we aligned with (or differ from) in this toolkit.

## manciuszz — Archive.org override (minimal)

- **Gist:** [downgrade_steam.ps1](https://gist.github.com/manciuszz/4e345e89facbf11c75eb3f09fa0b1952)
- **Platform:** Windows (`Steam.exe` in cwd)
- **Flow:** `-overridepackageurl` on Archive.org + `steam.cfg` with `BootStrapperInhibitAll=enable`

**Linux equivalent:** `apply_mirror.py` / `force_sep2024.py` with `-overridepackageurl http://127.0.0.1:8765/client …` and **`sep-steam`** (`STEAM_FORCE_CLIENT=ubuntu12_32`).

---

## rares478 — SteamTracking by date (destructive wipe)

- **Repo:** [rares478/Steam-Downgrader](https://github.com/rares478/Steam-Downgrader)
- **Linux equivalent:** `./downgrade fetch-by-date YYYY-MM-DD`, `nuke_client.py`, Fastly CDN fetch in `fetch_steamtracking.py`

SteamTracking **2024-09-13** → build **`1726256783`** (typical); Wayback **`20240913122103`** → **`1726604483`**.  
Sep **11** Wayback **`20240911122103`** → **`1726088054`** (what `force-sep2024` defaults to in `cache/`).

| Goal | Command |
|------|---------|
| Fetch Sep **11** ubuntu12 (Wayback) | `./downgrade force-wayback 20240911122103` or fetch only with same date |
| Fetch Sep **13** (different build) | `./downgrade force-wayback 20240913122103` |
| Install cached build only | `./downgrade force-sep2024 -y --cache-version-dir cache/<buildid>` |
| Switch Nov 7 build | `cache/1730853027` + `force-sep2024 -y --cache-version-dir …` |
