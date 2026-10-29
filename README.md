# steam-downgrader

> **Warning — read before running anything**
>
> This tool **permanently replaces large parts of your Steam client** under `~/.steam/debian-installation` (or `$STEAM_DIR`). It deletes modern client trees (`steamrt64/`, `ubuntu12_*`, UI assets, `package/`, configs) and reinstalls an old build. **Your games in `steamapps/` are not removed**, but Steam may not launch correctly until you restore.
>
> - **Quit Steam completely** before `./downgrade force-sep2024` (including tray/background).
> - **`force-sep2024` is destructive** — only client dirs are copied to `client_backup_*`; if backup or restore fails, you may need a full Steam reinstall.
> - While downgraded, **start Steam only with `./sep-steam`**. Launching `/usr/games/steam` normally can pull the current client again or leave a broken mix of versions.
> - To return to the current client: `./downgrade restore-current` then `steam -forcesteamupdate …` (see below). Until then, expect failed logins, crashes, or missing features.
> - **Use at your own risk.** Intended for developers and overlay/regression work, not everyday gaming on your only Steam install.

Linux toolkit to install a **Sep 2024** Steam client (`buildid` **1726088054**) from Wayback or SteamTracking — useful when you need the pre–SteamRT3 **`ubuntu12_32`** tree (overlay research, regression tests).

## Install

```bash
git clone https://github.com/d3nd3/steam-downgrader.git
cd steam-downgrader
```

Requires **Python 3.10+**, `/usr/games/steam`, and a normal install under `~/.steam/debian-installation`.

## Quick start (Sep 2024)

```bash
./downgrade fetch --wayback-date 20240913122103 --manifest steam_client_ubuntu12
# quit Steam first
./downgrade force-sep2024
./sep-steam
```

Or fetch via SteamTracking date (build may differ from Wayback — see [REFERENCES.md](REFERENCES.md)):

```bash
./downgrade fetch-by-date 2024-09-13
./downgrade force-sep2024
./sep-steam
```

**Start Steam only with `./sep-steam`** while downgraded. It sets `STEAM_FORCE_CLIENT=ubuntu12_32` so the launcher does not pick **steamrt64** (2026 client).

## What `force-sep2024` does

1. Backs up client dirs under `~/.steam/client_backup_*` (not `steamapps/`)
2. Wipes `steamrt64/`, `ubuntu12_*`, UI trees, etc. (`nuke_client.py`)
3. Re-bootstrap from `bootstrap.tar.xz`, stages `package/` from `cache/1726088054/`, force-extract via local mirror
4. **`sync_steam_executable`** — replaces `ubuntu12_32/steam` from **`steam_ubuntu12.zip.vz`** (Debian bootstrap often ships a **2025 stub** that segfaults against Sep libs)
5. Writes `steam.cfg`, creates **`./sep-steam`**

## Verification

- `package/steam_client_ubuntu12.manifest` contains `"version" "1726088054"`
- `ubuntu12_32/gameoverlayrenderer.so` mtime in **2024**
- No `steamrt64/` before launch
- Optional: set `STEAM_DOWNGRADER_WORKING_CLIENT=/path/to/steamclient.so` to SHA256-check `linux64/steamclient.so`

If verify warns the bootstrap stub is still in place:

```bash
./downgrade sync-steam
```

## Restore current client

```bash
./downgrade restore-current
steam -forcesteamupdate -forcepackagedownload -exitsteam
```

## Commands

| Command | Purpose |
|---------|---------|
| `./downgrade fetch …` | Download manifest + blobs into `cache/` |
| `./downgrade force-sep2024` | Destructive Sep 2024 install |
| `./downgrade sync-steam` | Fix `ubuntu12_32/steam` from cache only |
| `./downgrade lock-updates` | Write `steam.cfg` |
| `./downgrade restore-current` | Remove lock + print update flags |

Env: **`STEAM_DIR`** (default `~/.steam/debian-installation`).

See **[REFERENCES.md](REFERENCES.md)** for related public downgrade recipes.
