# steam-downgrader

Install an **older Linux Steam client** from the [Internet Archive Wayback Machine](https://web.archive.org/) (or SteamTracking) into `~/.steam/debian-installation`. Typical use: reproduce overlay bugs on a known build, then restore the current client.

> **Read this first**
>
> - **Quit Steam completely** (tray icon too) before any `force-*` command. Check with `./downgrade status`.
> - **`force-wayback` / `force-sep2024` replace most of the client** under `~/.steam/debian-installation`. **`steamapps/` (your games) are kept**, but backups only cover client trees (`client_backup_*`). If something goes wrong, use **Restore to latest Steam** below.
> - While downgraded, **always start with `./sep-steam`** (generated in this repo after install), not `/usr/games/steam` alone.
> - **At your own risk.** For developers and regression testing.

## Requirements

- Linux with Steam installed once (`/usr/games/steam`, `~/.steam/debian-installation`)
- **Python 3.10+**
- Network on first fetch (large download into `cache/` — not committed to git)

```bash
git clone https://github.com/d3nd3/steam-downgrader.git
cd steam-downgrader
chmod +x downgrade
```

---

## Step-by-step: install from a Wayback snapshot

Archive URL shape:  
`http://web.archive.org/web/<TIMESTAMP>if_/media.steampowered.com/client`

| Step | What to do |
|------|------------|
| 1 | Quit Steam (tray too). `./downgrade status` — **Steam processes** should be **none**. |
| 2 | Optional: `./downgrade verify-wayback <TIMESTAMP>` — want **302** (or success) for **`steam_client_ubuntu12`**. **`steam_client_steamrt64`** is often **404** on Archive; this tool still works via the ubuntu12 track + `./sep-steam`. |
| 3 | Fetch + install: `./downgrade force-wayback [-y] <TIMESTAMP> steam_client_ubuntu12` (type **`yes`** when prompted unless **`-y`**). |
| 4 | Start: **`./sep-steam`** |
| 5 | Confirm: **`./downgrade status`** — build id, overlay md5, **`steamrt64: no`**. |

Non-interactive: **`./downgrade force-wayback -y …`** or **`STEAM_DOWNGRADER_YES=1`**.

Optional: pin a **64-bit overlay** md5 after install (matches `~/.steam/bin64` → `ubuntu12_64`):

```bash
OVERLAY_MD5=b1e3ee47e947a4fff8a10df99ee26aa3 \
  ./downgrade force-wayback -y 20241107150153 steam_client_ubuntu12
# same flag on reinstall from cache:
./downgrade force-sep2024 -y --cache-version-dir cache/1730853027 \
  --overlay-md5 b1e3ee47e947a4fff8a10df99ee26aa3
```

---

## Wayback timestamp ≠ same build on nearby dates

Each Archive snapshot has its own **`"version"` build id** in the manifest. **Do not assume** “September 2024” is one build.

| Wayback timestamp | Manifest build | Notes |
|-------------------|----------------|--------|
| **`20240911122103`** | **`1726088054`** | Sep **11** — common “Sep 2024” research / working overlay era |
| **`20240913122103`** | **`1726604483`** | Sep **13** — *different* client, not `1726088054` |
| **`20240717082107`** | **`1721173382`** | Jul 17, 2024 |
| **`20241107150153`** | **`1730853027`** | Nov 7, 2024 (example overlay md5 `b1e3ee47…` on `ubuntu12_64`) |

To see what a snapshot would fetch **without** downloading blobs, only the manifest:

```bash
./downgrade fetch --wayback-date 20240911122103 --manifest steam_client_ubuntu12
# prints version=… and fills cache/<buildid>/ (re-run with existing cache skips blobs)
```

---

## Switch to another version you already downloaded

No need to hit Archive again if `cache/<buildid>/` is complete.

```bash
./downgrade list-cache
# quit Steam first
./downgrade force-sep2024 -y --cache-version-dir cache/1730853027   # Nov 7 example
./sep-steam

./downgrade force-sep2024 -y --cache-version-dir cache/1726088054   # Sep 11 example
./sep-steam
```

Plain **`./downgrade force-sep2024`** (no args) installs only from **`cache/1726088054/`** — fetch that build first if the folder is missing.

---

## Preset: Sep 11, 2024 build `1726088054`

Use the **Sep 11** snapshot (not Sep 13):

```bash
./downgrade force-wayback 20240911122103 steam_client_ubuntu12
./sep-steam
```

If **`cache/1726088054/`** already exists (from a prior fetch or copied from another machine):

```bash
./downgrade force-sep2024 -y
./sep-steam
```

SteamTracking by calendar date can differ from Wayback — see [REFERENCES.md](REFERENCES.md):

```bash
./downgrade fetch-by-date 2024-09-13
./downgrade list-cache
./downgrade force-sep2024 -y --cache-version-dir cache/<buildid-from-list>
```

---

## Copy `cache/` from another clone or PC

`cache/` is ~500 MB per build and is **gitignored**. To avoid re-downloading from Archive:

```bash
rsync -a /path/to/other/steam-downgrader/cache/1726088054/ ./cache/1726088054/
./downgrade force-sep2024 -y --cache-version-dir cache/1726088054
```

---

## Restore to latest Steam

| Step | Action |
|------|--------|
| 1 | **Quit Steam** (do not use `./sep-steam`). |
| 2 | **`./downgrade restore-current`** |
| 3 | **`steam -forcesteamupdate -forcepackagedownload -exitsteam`** |
| 4 | **`/usr/games/steam`** (normal launcher). |

Check: **`./downgrade status`**. If update fails, see **`ls -dt ~/.steam/client_backup_*`** or reinstall the distro **`steam`** package, then repeat step 3. **`steamapps/`** are not removed by this tool.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Steam still running | Quit all Steam; `./downgrade status` |
| Crash / assert on startup | `./downgrade sync-steam <buildid>` then `./sep-steam` |
| Wrong build after `force-wayback` | Wrong timestamp — see table above; reinstall with correct `cache/<buildid>` |
| Wrong overlay md5 | Reinstall with `--overlay-md5 …` or `OVERLAY_MD5=…` on `force-wayback` |
| Re-verify without wipe | `./downgrade force-sep2024 --skip-extract --cache-version-dir cache/<buildid>` |

---

## Commands

| Command | Purpose |
|---------|---------|
| `./downgrade status` | Build id, overlay md5, `steam.cfg`, running processes |
| `./downgrade list-cache` | Build ids under `cache/` |
| `./downgrade force-wayback [-y] TS [manifest]` | Fetch + full install |
| `./downgrade force-sep2024 [-y] [--cache-version-dir cache/BUILD]` | Install from cache (default `1726088054`) |
| `./downgrade fetch --wayback-date TS --manifest …` | Download only |
| `./downgrade sync-steam [buildid]` | Fix `ubuntu12_32/steam` from cache |
| `./downgrade verify-wayback TS` | Probe Archive URLs |
| `./downgrade restore-current` | Unlock updates + restore instructions |

**Flags (Python entrypoints):** `--cache-version-dir`, `--manifest-basename`, `--overlay-md5`, `--skip-extract`, `-y` / `--yes`.

**Environment:** `STEAM_DIR`, `OVERLAY_MD5`, `STEAM_DOWNGRADER_YES=1`, `STEAM_DOWNGRADER_WORKING_CLIENT`.

---

## What a full install does

1. Backup → `client_backup_*`
2. Wipe client trees (`steamrt64/`, `ubuntu12_*`, UI, …)
3. Bootstrap + stage `package/` from `cache/<buildid>/`
4. Local mirror extract (same idea as `-overridepackageurl` + `-forcepackagedownload`)
5. Sync real **`ubuntu12_32/steam`** from `steam_ubuntu12.zip.vz`
6. Write **`steam.cfg`**, create **`./sep-steam`**

More context: [REFERENCES.md](REFERENCES.md).
