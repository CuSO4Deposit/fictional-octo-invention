"""Generate JSON data from Y-Offline database for static page building."""

import json
import time
import tomllib
from pathlib import Path

from y_offline.arcaea.utils import create_manager as arcaea_create_manager
from y_offline.pjsk.utils import create_manager as pjsk_create_manager
from y_offline.utils import Config

DATA_DIR = Path("data")

ARCAEA_DIFF_NAMES = {0: "Past", 1: "Present", 2: "Future", 3: "Beyond", 4: "Eternal"}
PJSK_DIFF_NAMES = {
    0: "Easy",
    1: "Normal",
    2: "Hard",
    3: "Expert",
    4: "Master",
    5: "Append",
}

DEFAULT_PJSK_CDN = "https://storage.sekai.best/sekai-jp-assets"


def load_config() -> tuple[Config, dict]:
    with open("config.toml", "rb") as f:
        raw = tomllib.load(f)
    config = Config.model_validate(raw)
    pages = raw.get("pages", {})
    return config, pages


def arcaea_jacket_url(song_id: str) -> str:
    return f"https://wiki.arcaea.cn/index.php/Special:FilePath/Songs_{song_id}.jpg"


def pjsk_jacket_url(song_id: str, asset_map: dict[str, str], cdn: str) -> str:
    name = asset_map.get(song_id, f"jacket_s_{int(song_id):03d}")
    return f"{cdn}/music/jacket/{name}/{name}.webp"


def serialize_arcaea_record(r) -> dict:
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
        "jacket_url": arcaea_jacket_url(r.song_id),
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
        "jacket_url": pjsk_jacket_url(r.song_id, asset_map, cdn),
    }


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

    b30_ptt = sum(r.play_ptt for r in b30) / max(len(b30), 1)
    r10_ptt = sum(r.play_ptt for r in r10) / max(len(r10), 1)
    ptt = sum(r.play_ptt for r in b30 + r10) / 40

    data = {
        "user": user,
        "generated_at": int(time.time()),
        "ptt": round(ptt, 4),
        "b30_ptt": round(b30_ptt, 4),
        "r10_ptt": round(r10_ptt, 4),
        "b30": [serialize_arcaea_record(r) for r in b30],
        "r30": [serialize_arcaea_record(r) for r in r30],
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


def main():
    config, pages = load_config()
    user = pages.get("user", "unknown")
    cdn = pages.get("pjsk_jacket_cdn", DEFAULT_PJSK_CDN)

    DATA_DIR.mkdir(exist_ok=True)

    if config.arcaea:
        generate_arcaea(config, user)
    if config.pjsk:
        generate_pjsk(config, user, cdn)

    print("Done.")


if __name__ == "__main__":
    main()
