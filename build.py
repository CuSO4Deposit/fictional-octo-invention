"""Build static HTML pages from generated JSON data."""

import json
import shutil
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

DATA_DIR = Path("data")
DIST_DIR = Path("dist")
TEMPLATE_DIR = Path("templates")
STATIC_DIR = Path("static")


def time_ago(timestamp: int) -> str:
    diff = int(time.time()) - timestamp
    if diff < 60:
        return f"{diff}s ago"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


def load_json(name: str) -> dict | None:
    path = DATA_DIR / name
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def comma(value: int) -> str:
    return f"{value:,}"


def main():
    DIST_DIR.mkdir(exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    env.filters["time_ago"] = time_ago
    env.filters["comma"] = comma

    arcaea = load_json("arcaea.json")
    pjsk = load_json("pjsk.json")

    ctx = {"arcaea": arcaea, "pjsk": pjsk, "base": ""}

    # Index
    html = env.get_template("index.html").render(**ctx)
    (DIST_DIR / "index.html").write_text(html)

    # Arcaea pages
    if arcaea:
        html = env.get_template("arcaea_b30.html").render(data=arcaea, **ctx)
        (DIST_DIR / "arcaea_b30.html").write_text(html)
        html = env.get_template("arcaea_r30.html").render(data=arcaea, **ctx)
        (DIST_DIR / "arcaea_r30.html").write_text(html)

    # PJSK pages
    if pjsk:
        html = env.get_template("pjsk_b30.html").render(data=pjsk, **ctx)
        (DIST_DIR / "pjsk_b30.html").write_text(html)

    # Copy static assets
    dist_static = DIST_DIR / "static"
    if dist_static.exists():
        shutil.rmtree(dist_static)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, dist_static)

    pages = list(DIST_DIR.glob("*.html"))
    print(f"Built {len(pages)} pages in {DIST_DIR}/")


if __name__ == "__main__":
    main()
