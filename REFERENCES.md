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

SteamTracking **2024-09-13** → build **`1726256783`**; Wayback **`20240913122103`** → **`1726088054`** (what `force-sep2024` targets).

---

## This toolkit map

| Goal | Command |
|------|---------|
| Fetch Sep-era ubuntu12 (SteamTracking) | `./downgrade fetch-by-date 2024-09-13` |
| Fetch from Wayback | `./downgrade fetch --wayback-date 20240913122103 --manifest steam_client_ubuntu12` |
| Destructive install + lock | `./downgrade force-sep2024` |
| Launch (no steamrt64) | `./sep-steam` |
