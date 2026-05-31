"""Generate JSON data from Y-Offline database for static page building."""

import json
import ssl
import time
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

from y_offline.arcaea.utils import create_manager as arcaea_create_manager
from y_offline.cytus2.utils import create_manager as cytus2_create_manager
from y_offline.pjsk.utils import create_manager as pjsk_create_manager
from y_offline.utils import Config

DATA_DIR = Path("data")
JACKET_DIR = DATA_DIR / "jackets"
JACKET_SIZE = 160

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

ARCAEA_DIFF_NAMES = {0: "Past", 1: "Present", 2: "Future", 3: "Beyond", 4: "Eternal"}
PJSK_DIFF_NAMES = {
    0: "Easy",
    1: "Normal",
    2: "Hard",
    3: "Expert",
    4: "Master",
    5: "Append",
}

CYTUS2_DIFF_NAMES = {
    0: "Easy",
    1: "Hard",
    2: "Chaos",
    3: "Glitch",
    4: "Crash",
}

DEFAULT_PJSK_CDN = "https://storage.sekai.best/sekai-jp-assets"
DEFAULT_CYTUS2_CDN = "https://wiki.biligame.com/cytus2/Special:FilePath"


def load_config() -> tuple[Config, dict]:
    with open("config.toml", "rb") as f:
        raw = tomllib.load(f)
    config = Config.model_validate(raw)
    pages = raw.get("pages", {})
    return config, pages


def download_jacket(url: str, local_path: Path, crop_square: bool = False) -> None:
    """Download jacket image if not already cached, resize to JACKET_SIZE.

    When crop_square is True, the image is center-cropped to a 1:1 square
    before resizing — used for sources where covers are not uniformly square
    (e.g. bilibili wiki Cytus II banners are sometimes 3:1).
    """
    if local_path.exists():
        return
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
                    "y-offline-pages/0.1"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
            local_path.write_bytes(resp.read())
        img = Image.open(local_path)
        if crop_square:
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
        img.thumbnail((JACKET_SIZE, JACKET_SIZE))
        img.save(local_path)
    except Exception as e:
        print(f"  Warning: failed to download {url}: {e}")
        if local_path.exists():
            local_path.unlink()


JACKET_OVERRIDES_PATH = Path("arcaea_jacket_overrides.json")
CYTUS2_JACKET_OVERRIDES_PATH = Path("cytus2_jacket_overrides.json")


def _load_arcaea_overrides() -> dict[str, str]:
    """Load song_id -> full jacket URL overrides."""
    if JACKET_OVERRIDES_PATH.exists():
        with open(JACKET_OVERRIDES_PATH) as f:
            return json.load(f)
    return {}


def _load_cytus2_overrides() -> dict[str, str]:
    """Load song_id -> full jacket URL overrides for Cytus II."""
    if CYTUS2_JACKET_OVERRIDES_PATH.exists():
        with open(CYTUS2_JACKET_OVERRIDES_PATH) as f:
            return json.load(f)
    return {}


def arcaea_jacket(
    song_id: str, name_en: str, name_jp: str | None, overrides: dict[str, str]
) -> str:
    """Download Arcaea jacket and return local relative path."""
    local = JACKET_DIR / "arcaea" / f"{song_id}.webp"
    if song_id in overrides:
        url = overrides[song_id]
    else:
        page_name = urllib.parse.quote(name_jp or name_en)
        file_name = urllib.parse.quote(name_en)
        url = f"https://cdn.wikiwiki.jp/to/w/arcaea/{page_name}/::ref/{file_name}.jpg.webp"
    download_jacket(url, local)
    return f"jackets/arcaea/{song_id}.webp"


def pjsk_jacket(song_id: str, asset_map: dict[str, str], cdn: str) -> str:
    """Download PJSK jacket and return local relative path."""
    name = asset_map.get(song_id, f"jacket_s_{int(song_id):03d}")
    url = f"{cdn}/music/jacket/{name}/{name}.webp"
    local = JACKET_DIR / "pjsk" / f"{song_id}.webp"
    download_jacket(url, local)
    return f"jackets/pjsk/{song_id}.webp"


def cytus2_jacket(song_id: str, name: str, overrides: dict[str, str], cdn: str) -> str:
    """Download Cytus II jacket from bilibili wiki and return local relative path.

    Looks up `{cdn}/{name with spaces->_}.png` via MediaWiki Special:FilePath,
    which 302-redirects to the actual image. Falls back to overrides keyed by
    song_id when the name doesn't resolve cleanly (e.g. disambiguated titles).
    """
    local = JACKET_DIR / "cytus2" / f"{song_id}.webp"
    if song_id in overrides:
        url = overrides[song_id]
    else:
        page_name = urllib.parse.quote(name.replace(" ", "_"))
        url = f"{cdn}/{page_name}.png"
    download_jacket(url, local, crop_square=True)
    return f"jackets/cytus2/{song_id}.webp"


def serialize_arcaea_record(
    r,
    name_jp_map: dict[str, str | None],
    name_en_map: dict[str, str],
    overrides: dict[str, str],
) -> dict:
    name_jp = name_jp_map.get(r.song_id)
    name_en = name_en_map.get(r.song_id, r.name)
    return {
        "song_id": r.song_id,
        "name": r.name,
        "rating_class": r.rating_class,
        "difficulty": ARCAEA_DIFF_NAMES.get(r.rating_class, "?"),
        "rating": r.rating,
        "score": r.score,
        "play_ptt": round(r.play_ptt, 4),
        "pure": r.pure,
        "max_pure": r.max_pure,
        "far": r.far,
        "lost": r.lost,
        "accuracy": round(r.accuracy(), 6),
        "time": r.time,
        "jacket_url": arcaea_jacket(r.song_id, name_en, name_jp, overrides),
    }


def serialize_pjsk_record(r, asset_map: dict[str, str], cdn: str) -> dict:
    return {
        "song_id": r.song_id,
        "name": r.name,
        "rating_class": r.rating_class,
        "difficulty": PJSK_DIFF_NAMES.get(r.rating_class, "?"),
        "rating": r.rating,
        "metric": round(r.metric(), 4),
        "perfect": r.perfect,
        "great": r.great,
        "good": r.good,
        "bad": r.bad,
        "miss": r.miss,
        "accuracy": round(r.accuracy(), 6),
        "time": r.time,
        "jacket_url": pjsk_jacket(r.song_id, asset_map, cdn),
    }


def serialize_cytus2_record(r, overrides: dict[str, str], cdn: str) -> dict:
    total = r.sp + r.p + r.g + r.b + r.m
    return {
        "song_id": r.song_id,
        "name": r.name,
        "rating_class": r.rating_class,
        "difficulty": CYTUS2_DIFF_NAMES.get(r.rating_class, "?"),
        "rating": r.rating,
        "metric": round(r.metric(), 4),
        "sp": r.sp,
        "p": r.p,
        "g": r.g,
        "b": r.b,
        "m": r.m,
        "note": r.note,
        "total": total,
        "accuracy": round(r.accuracy(), 6),
        "time": r.time,
        "jacket_url": cytus2_jacket(r.song_id, r.name, overrides, cdn),
    }


def serialize_arcaea_recent_record(
    r,
    name_jp_map: dict[str, str | None],
    name_en_map: dict[str, str],
    overrides: dict[str, str],
) -> dict:
    data = serialize_arcaea_record(r, name_jp_map, name_en_map, overrides)
    data["game"] = "arcaea"
    return data


def serialize_pjsk_recent_record(r, asset_map: dict[str, str], cdn: str) -> dict:
    data = serialize_pjsk_record(r, asset_map, cdn)
    data["game"] = "pjsk"
    return data


def serialize_cytus2_recent_record(r, overrides: dict[str, str], cdn: str) -> dict:
    data = serialize_cytus2_record(r, overrides, cdn)
    data["game"] = "cytus2"
    return data


def build_pjsk_asset_map(musics_path: Path) -> dict[str, str]:
    """Build song_id -> assetbundleName mapping from musics.json."""
    with open(musics_path) as f:
        musics = json.load(f)
    return {str(m["id"]): m["assetbundleName"] for m in musics}


def generate_arcaea(config: Config, user: str) -> None:
    mgr = arcaea_create_manager(config)
    b30 = mgr.b30(user)
    r30 = mgr.r30(user)
    r10 = mgr.r10(user)

    # Build song_id -> name maps from chart repo
    name_jp_map: dict[str, str | None] = {}
    name_en_map: dict[str, str] = {}
    for chart in mgr.chart_repo.all_charts():
        if chart.song_id not in name_jp_map:
            name_jp_map[chart.song_id] = chart.name_jp
            name_en_map[chart.song_id] = chart.name_en

    overrides = _load_arcaea_overrides()

    b30_ptt = sum(r.play_ptt for r in b30) / max(len(b30), 1)
    r10_ptt = sum(r.play_ptt for r in r10) / max(len(r10), 1)
    ptt = sum(r.play_ptt for r in b30 + r10) / 40

    def ser(r):
        return serialize_arcaea_record(r, name_jp_map, name_en_map, overrides)

    data = {
        "user": user,
        "generated_at": int(time.time()),
        "ptt": round(ptt, 4),
        "b30_ptt": round(b30_ptt, 4),
        "r10_ptt": round(r10_ptt, 4),
        "b30": [ser(r) for r in b30],
        "r30": [ser(r) for r in r30],
    }

    out = DATA_DIR / "arcaea.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Generated {out} ({len(b30)} b30, {len(r30)} r30)")


def generate_pjsk(config: Config, user: str, cdn: str) -> None:
    mgr = pjsk_create_manager(config)
    asset_map = build_pjsk_asset_map(config.pjsk.musics_json_path)
    b30 = mgr.best(user)

    data = {
        "user": user,
        "generated_at": int(time.time()),
        "b30": [serialize_pjsk_record(r, asset_map, cdn) for r in b30],
    }

    out = DATA_DIR / "pjsk.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Generated {out} ({len(b30)} b30)")


def generate_cytus2(config: Config, user: str, cdn: str) -> None:
    mgr = cytus2_create_manager(config)
    b30 = mgr.best(user)
    overrides = _load_cytus2_overrides()

    b30_metric = sum(r.metric() for r in b30) / max(len(b30), 1)

    data = {
        "user": user,
        "generated_at": int(time.time()),
        "b30_metric": round(b30_metric, 4),
        "b30": [serialize_cytus2_record(r, overrides, cdn) for r in b30],
    }

    out = DATA_DIR / "cytus2.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Generated {out} ({len(b30)} b30)")


def generate_recent(config: Config, user: str, cdn: str) -> None:
    recent: list[dict] = []

    if config.arcaea:
        mgr = arcaea_create_manager(config)
        name_jp_map: dict[str, str | None] = {}
        name_en_map: dict[str, str] = {}
        for chart in mgr.chart_repo.all_charts():
            if chart.song_id not in name_jp_map:
                name_jp_map[chart.song_id] = chart.name_jp
                name_en_map[chart.song_id] = chart.name_en
        overrides = _load_arcaea_overrides()
        recent.extend(
            serialize_arcaea_recent_record(r, name_jp_map, name_en_map, overrides)
            for r in mgr._select_play_record(
                "arcaea_record", user=user, limit=30, order=("[time]", "DESC")
            )
        )

    if config.pjsk:
        mgr = pjsk_create_manager(config)
        asset_map = build_pjsk_asset_map(config.pjsk.musics_json_path)
        recent.extend(
            serialize_pjsk_recent_record(r, asset_map, cdn) for r in mgr.records(user)
        )

    if config.cytus2:
        mgr = cytus2_create_manager(config)
        cytus2_overrides = _load_cytus2_overrides()
        recent.extend(
            serialize_cytus2_recent_record(r, cytus2_overrides, DEFAULT_CYTUS2_CDN)
            for r in mgr._select_play_record("cytus2_record", user=user, limit=30)
        )

    recent.sort(key=lambda r: r["time"], reverse=True)
    data = {
        "user": user,
        "generated_at": int(time.time()),
        "recent": recent[:30],
    }

    out = DATA_DIR / "recent.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Generated {out} ({len(data['recent'])} recent)")


def main():
    config, pages = load_config()
    user = pages.get("user", "unknown")
    cdn = pages.get("pjsk_jacket_cdn", DEFAULT_PJSK_CDN)

    DATA_DIR.mkdir(exist_ok=True)

    if config.arcaea:
        generate_arcaea(config, user)
    if config.pjsk:
        generate_pjsk(config, user, cdn)
    if config.cytus2:
        generate_cytus2(config, user, DEFAULT_CYTUS2_CDN)
    if config.arcaea or config.pjsk or config.cytus2:
        generate_recent(config, user, cdn)

    print("Done.")


if __name__ == "__main__":
    main()
