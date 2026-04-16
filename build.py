"""Build static HTML pages from generated JSON data."""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

DATA_DIR = Path("data")
DIST_DIR = Path("dist")
TEMPLATE_DIR = Path("templates")
STATIC_DIR = Path("static")


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
    env.filters["comma"] = comma

    arcaea = load_json("arcaea.json")
    pjsk = load_json("pjsk.json")
    recent = load_json("recent.json")

    ctx = {"arcaea": arcaea, "pjsk": pjsk, "recent": recent, "base": ""}

    # Index defaults to Recent when available.
    index_template = "recent.html" if recent else "index.html"
    index_data = recent if recent else None
    if index_data is None:
        html = env.get_template(index_template).render(**ctx)
    else:
        html = env.get_template(index_template).render(data=index_data, **ctx)
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

    if recent:
        html = env.get_template("recent.html").render(data=recent, **ctx)
        (DIST_DIR / "recent.html").write_text(html)

    # Copy static assets
    dist_static = DIST_DIR / "static"
    if dist_static.exists():
        shutil.rmtree(dist_static)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, dist_static)

    # Copy jacket images
    jackets_src = DATA_DIR / "jackets"
    jackets_dst = DIST_DIR / "jackets"
    if jackets_dst.exists():
        shutil.rmtree(jackets_dst)
    if jackets_src.exists():
        shutil.copytree(jackets_src, jackets_dst)

    pages = list(DIST_DIR.glob("*.html"))
    print(f"Built {len(pages)} pages in {DIST_DIR}/")


if __name__ == "__main__":
    main()
