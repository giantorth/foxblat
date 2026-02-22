import os
import re
import subprocess
import psutil
from dataclasses import dataclass


@dataclass
class SteamGame:
    app_id: str
    name: str

    def __repr__(self):
        return f"SteamGame(app_id='{self.app_id}', name='{self.name}')"


def get_steam_library_paths() -> list[str]:
    """Return all Steam steamapps directories (native and Flatpak, including extra libraries)."""
    paths = []
    _path_re = re.compile(r'"path"\s+"([^"]+)"', re.IGNORECASE)

    base_dirs = [
        os.path.expanduser("~/.local/share/Steam"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam"),
    ]

    for base in base_dirs:
        default_steamapps = os.path.join(base, "steamapps")
        if os.path.isdir(default_steamapps) and default_steamapps not in paths:
            paths.append(default_steamapps)

        # libraryfolders.vdf lists every Steam library location the user has set up
        vdf_path = os.path.join(default_steamapps, "libraryfolders.vdf")
        if not os.path.isfile(vdf_path):
            continue
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for match in _path_re.finditer(content):
                extra = os.path.join(match.group(1), "steamapps")
                if os.path.isdir(extra) and extra not in paths:
                    paths.append(extra)
        except OSError:
            pass

    return paths


_app_names_cache: dict[str, str] = {}


def _scan_steam_app_names() -> dict[str, str]:
    app_names: dict[str, str] = {}
    name_re = re.compile(r'"name"\s+"([^"]+)"', re.IGNORECASE)
    appid_re = re.compile(r'"appid"\s+"(\d+)"', re.IGNORECASE)

    for library_path in get_steam_library_paths():
        try:
            for entry in os.listdir(library_path):
                if not entry.startswith("appmanifest_") or not entry.endswith(".acf"):
                    continue
                acf_path = os.path.join(library_path, entry)
                try:
                    with open(acf_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    appid_match = appid_re.search(content)
                    name_match = name_re.search(content)
                    if appid_match and name_match:
                        app_names[appid_match.group(1)] = name_match.group(1)
                except OSError:
                    continue
        except OSError:
            continue

    return app_names


def lookup_steam_app_name(app_id: str) -> str:
    """Return the game name for the given AppID.

    The ACF manifest data is loaded once and cached for the lifetime of the
    process. If an AppID is not found in the cache (e.g. a game installed
    mid-session), the manifests are re-scanned once to pick up new entries.
    """
    global _app_names_cache

    if not _app_names_cache:
        _app_names_cache = _scan_steam_app_names()

    if app_id not in _app_names_cache:
        # Game may have been installed after startup — refresh once
        _app_names_cache = _scan_steam_app_names()

    return _app_names_cache.get(app_id, f"Steam App {app_id}")


# Known Steam infrastructure process names (read from /proc/{pid}/comm) that
# retain SteamAppId in their environment after a game exits.  Identified by
# scanning live system output — see _detect_steam_games_native().
_STEAM_INFRA_COMM = frozenset({
    # Steam client and helpers
    "steam",
    "steamwebhelper",
    "steam-runtime-setup",
    # Steam Linux Runtime container processes (persist between game sessions)
    "srt-bwrap",
    "steam-runtime-launcher-service",
    # Process reaper and pressure-vessel wrappers
    # (Linux truncates comm to 15 chars, so "pressure-vessel-adverb" → "pv-adverb")
    "reaper",
    "pressure-vessel-wrap",
    "pressure-vessel-adverb",
    "pv-adverb",
    # Shader pre-compilation (lingers after game exit)
    "fossilize_replay",
    # Wine server (outlives other Wine processes after game exit)
    "wineserver",
    "wineserver64",
})


def _detect_steam_games_native() -> list[SteamGame]:
    """Detect running Steam games by reading process environments (native mode).

    Uses /proc/{pid}/comm (process name) to skip known Steam infrastructure
    that retains SteamAppId in its environment even when no game is running.
    """
    seen_ids: set[str] = set()
    games: list[SteamGame] = []

    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] in _STEAM_INFRA_COMM:
                continue
            env = proc.environ()
            app_id = env.get("SteamAppId") or env.get("SteamGameId")
            if not app_id or app_id == "0":
                continue
            if app_id in seen_ids:
                continue
            seen_ids.add(app_id)
            games.append(SteamGame(app_id=app_id, name=lookup_steam_app_name(app_id)))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return games


def _detect_steam_games_flatpak() -> list[SteamGame]:
    """Detect running Steam games via flatpak-spawn (Flatpak sandbox mode).

    Uses /proc/{pid}/comm to skip the same known infrastructure processes.
    """
    seen_ids: set[str] = set()
    games: list[SteamGame] = []

    # Read comm per-pid; skip infrastructure; then extract SteamAppId/SteamGameId from environ.
    infra_pattern = "|".join(_STEAM_INFRA_COMM)
    script = (
        "for pid in /proc/[0-9]*/; do "
        "  comm=$(cat ${pid}comm 2>/dev/null); "
        f"  case $comm in {infra_pattern}) continue;; esac; "
        "  env=$(cat ${pid}environ 2>/dev/null | tr '\\0' '\\n' | grep -E '^Steam(App|Game)Id='); "
        "  [ -n \"$env\" ] && echo \"$env\"; "
        "done"
    )

    try:
        result = subprocess.check_output(
            ["flatpak-spawn", "--host", "bash", "-c", script],
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        for line in result.decode(errors="replace").splitlines():
            line = line.strip()
            if not (line.startswith("SteamAppId=") or line.startswith("SteamGameId=")):
                continue
            app_id = line.split("=", 1)[1].strip()
            if not app_id or app_id == "0":
                continue
            if app_id in seen_ids:
                continue
            seen_ids.add(app_id)
            games.append(SteamGame(app_id=app_id, name=lookup_steam_app_name(app_id)))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return games


def detect_running_steam_games() -> list[SteamGame]:
    """Return a list of currently running Steam games.

    Uses environment variable inspection to find processes with SteamAppId set,
    then maps AppIDs to game names from installed ACF manifests.
    """
    if os.environ.get("FOXBLAT_FLATPAK_EDITION") == "true":
        return _detect_steam_games_flatpak()
    return _detect_steam_games_native()
